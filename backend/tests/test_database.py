import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.database import init_db
from tests.conftest import TEST_DATABASE_URL


async def test_init_db_is_idempotent(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///%s" % (tmp_path / "t.db"))
    try:
        await init_db(engine)
        await init_db(engine)  # second call must be a no-op, not an error
        async with engine.begin() as conn:
            tables = {row[0] for row in await conn.execute(text("select name from sqlite_master where type='table'"))}
        assert {"users", "shifts", "action_logs"} <= tables
    finally:
        await engine.dispose()


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs PostgreSQL: set TEST_DATABASE_URL")
async def test_several_workers_can_create_the_schema_at_the_same_time():
    setup = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with setup.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await setup.dispose()

    async def worker():
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        try:
            await init_db(engine)
        finally:
            await engine.dispose()

    # Without the advisory lock three of these four fail with a duplicate-type UniqueViolation.
    await asyncio.gather(*[worker() for _ in range(4)])
