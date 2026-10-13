import { MessageView } from "../types";

type InboxProps = {
  inbox: MessageView[];
  disabled: boolean;
  onCommand: (command: string) => void;
};

const Inbox = ({ inbox, disabled, onCommand }: InboxProps) => (
  <section className="card inbox" aria-label="Inbox">
    <h2 className="card-title">Inbox ({inbox.length})</h2>
    {inbox.length === 0 && <p className="empty-state">Nothing waiting. Try &quot;wait&quot;.</p>}
    <ul className="inbox-list">
      {inbox.map((message) => (
        <li key={message.id} className={`inbox-item priority-${message.priority}`}>
          <div className="inbox-head">
            <span className="inbox-id">
              {!message.read && (
                <>
                  <span aria-hidden="true">* </span>
                  <span className="visually-hidden">Unread </span>
                </>
              )}
              {message.id}
            </span>
            <span className="inbox-priority">
              P{message.priority}
              {message.due && <span className="inbox-due"> · due {message.due}</span>}
            </span>
          </div>
          <div className="inbox-title">
            {message.sender}: {message.title}
          </div>
          <div className="inbox-actions">
            {message.read ? (
              message.verbs.map(({ verb, label }) => (
                <button
                  key={verb}
                  type="button"
                  className="button button-secondary button-small"
                  title={label}
                  aria-label={`${verb} ${message.id}: ${label}`}
                  disabled={disabled}
                  onClick={() => onCommand(`${verb} ${message.id}`)}
                >
                  {verb}
                </button>
              ))
            ) : (
              <button
                type="button"
                className="button button-secondary button-small"
                aria-label={`read ${message.id}`}
                disabled={disabled}
                onClick={() => onCommand(`read ${message.id}`)}
              >
                read
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  </section>
);

export default Inbox;
