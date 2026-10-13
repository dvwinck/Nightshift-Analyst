import { useEffect, useRef } from "react";

import CommandInput from "../components/CommandInput";
import Hud from "../components/Hud";
import Inbox from "../components/Inbox";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import { useShift } from "../hooks/useShift";

/** Keep following new output only while the player has not scrolled up to read. */
const NEAR_BOTTOM_PX = 48;

const TerminalPage = () => {
  const { token, expireSession } = useAuth();
  const { shift, lines, status, busy, error, load, start, send } = useShift(token, expireSession);
  const outputRef = useRef<HTMLDivElement>(null);
  const followOutput = useRef(true);
  const newShiftRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const output = outputRef.current;
    if (output && followOutput.current) output.scrollTop = output.scrollHeight;
  }, [lines]);

  const ended = shift?.view.ending ?? null;

  useEffect(() => {
    // The input unmounts when the shift ends; send keyboard focus somewhere useful.
    if (ended) newShiftRef.current?.focus();
  }, [ended]);

  const trackScroll = () => {
    const output = outputRef.current;
    if (!output) return;
    followOutput.current =
      output.scrollHeight - output.scrollTop - output.clientHeight <= NEAR_BOTTOM_PX;
  };

  return (
    <Layout subtitle="Night shift console">
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {status === "loading" && <p className="empty-state">Connecting to console...</p>}

      {status === "error" && (
        <button type="button" className="button" onClick={load}>
          Retry
        </button>
      )}

      {status === "none" && (
        <section className="card">
          <h2 className="card-title">No shift in progress</h2>
          <p>Your console is dark. Clock in when you are ready.</p>
          <button type="button" className="button" onClick={start} disabled={busy}>
            Start shift
          </button>
        </section>
      )}

      {status === "ready" && shift && (
        <div className="terminal-layout">
          <section className="terminal" aria-label="Terminal">
            <div
              className="terminal-output"
              ref={outputRef}
              onScroll={trackScroll}
              role="log"
              aria-label="Console output"
            >
              {lines.map((line) => (
                <p key={line.id} className={`line line-${line.kind}`}>
                  {line.text}
                </p>
              ))}
            </div>
            {ended ? (
              <div className="ending-banner">
                <strong>{ended.title}</strong>
                <button
                  type="button"
                  className="button"
                  ref={newShiftRef}
                  onClick={start}
                  disabled={busy}
                >
                  Start new shift
                </button>
              </div>
            ) : (
              <CommandInput inbox={shift.view.inbox} disabled={busy} onSubmit={send} />
            )}
          </section>
          <aside className="terminal-side">
            <Hud view={shift.view} />
            <Inbox inbox={shift.view.inbox} disabled={busy || ended !== null} onCommand={send} />
          </aside>
        </div>
      )}
    </Layout>
  );
};

export default TerminalPage;
