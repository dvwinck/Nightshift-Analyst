import { Case } from "../types";

type CaseCardProps = {
  caseData: Case;
};

const statusLabels: Record<Case["status"], string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  failed: "Failed",
};

const difficultyLabels: Record<Case["difficulty"], string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
  extreme: "Extreme",
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const CaseCard = ({ caseData }: CaseCardProps) => {
  return (
    <article className="card">
      <header className="card-header">
        <div>
          <h3 className="card-title">{caseData.title}</h3>
          <p className="card-subtitle">{difficultyLabels[caseData.difficulty]}</p>
        </div>
        <span className={`status-pill status-${caseData.status}`}>
          {statusLabels[caseData.status]}
        </span>
      </header>
      <p className="card-description">{caseData.description}</p>
      <dl className="card-grid">
        <div>
          <dt>Time Limit</dt>
          <dd>{caseData.time_limit_minutes} minutes</dd>
        </div>
        <div>
          <dt>Stress Impact</dt>
          <dd>{caseData.stress_impact}</dd>
        </div>
        <div>
          <dt>Reputation Reward</dt>
          <dd>{caseData.reputation_reward}</dd>
        </div>
        <div>
          <dt>Clues Found</dt>
          <dd>
            {caseData.clues_found} / {caseData.total_clues}
          </dd>
        </div>
      </dl>
      <footer className="card-footer">
        <span>Created {dateFormatter.format(new Date(caseData.created_at))}</span>
        {caseData.completed_at ? (
          <span>Completed {dateFormatter.format(new Date(caseData.completed_at))}</span>
        ) : caseData.started_at ? (
          <span>Started {dateFormatter.format(new Date(caseData.started_at))}</span>
        ) : null}
      </footer>
    </article>
  );
};

export default CaseCard;
