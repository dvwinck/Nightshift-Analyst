"""A tiny hand-built shift so rule tests state exactly what they depend on."""

from app.engine.models import ShiftContent


def tiny_content(**overrides) -> ShiftContent:
    data = {
        "title": "Tiny",
        "intro": "hello",
        "start_hour": 22,
        "shift_length_minutes": 120,
        "messages": [
            {
                "id": "alert-1",
                "category": "alert",
                "priority": 2,
                "sender": "SYSMON",
                "title": "Disk almost full",
                "body": "Disk at 95%.",
                "arrives_at": 0,
                "expires_at": 60,
                "on_timeout": {"text": "The disk filled up.", "effects": {"technical": -8}},
                "responses": {
                    "execute": {
                        "label": "Clean it",
                        "text": "Cleaned.",
                        "effects": {"technical": 5, "ethical": -3, "set_flags": ["cleaned"]},
                    },
                    "deny": {"label": "Ignore", "text": "Ignored.", "effects": {"technical": -5}},
                    "delay": {"label": "Later", "text": "Later."},
                },
            },
            {
                "id": "order-2",
                "category": "order",
                "priority": 4,
                "sender": "DIRECTORATE",
                "title": "Follow-up",
                "body": "Report back.",
                "arrives_at": 30,
                "requires": {"flags_all": ["cleaned"]},
                "responses": {"execute": {"label": "Report", "text": "Reported."}},
            },
        ],
        "endings": [
            {"id": "good", "title": "Good", "text": "ok", "priority": 5, "requires": {"flags_all": ["cleaned"]}},
            {"id": "plain", "title": "Plain", "text": "meh"},
        ],
    }
    data.update(overrides)
    return ShiftContent.model_validate(data)
