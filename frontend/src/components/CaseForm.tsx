import { FormEvent, useState } from "react";

import { CaseCreatePayload, CaseDifficulty, CaseStatus } from "../types";

const difficulties: CaseDifficulty[] = ["easy", "medium", "hard", "extreme"];
const statuses: CaseStatus[] = ["pending", "in_progress", "completed", "failed"];

type CaseFormProps = {
  userId: string;
  onCreate: (payload: CaseCreatePayload) => Promise<void> | void;
  isSubmitting?: boolean;
};

const CaseForm = ({ userId, onCreate, isSubmitting = false }: CaseFormProps) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState<CaseDifficulty>("medium");
  const [status, setStatus] = useState<CaseStatus>("pending");
  const [timeLimit, setTimeLimit] = useState(15);
  const [stressImpact, setStressImpact] = useState(10);
  const [reputationReward, setReputationReward] = useState(20);
  const [totalClues, setTotalClues] = useState(3);

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setDifficulty("medium");
    setStatus("pending");
    setTimeLimit(15);
    setStressImpact(10);
    setReputationReward(20);
    setTotalClues(3);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!title.trim() || !description.trim()) {
      return;
    }

    try {
      await onCreate({
        user_id: userId,
        title: title.trim(),
        description: description.trim(),
        difficulty,
        status,
        time_limit_minutes: Number(timeLimit),
        stress_impact: Number(stressImpact),
        reputation_reward: Number(reputationReward),
        total_clues: Number(totalClues),
        clues_found: 0,
      });
      resetForm();
    } catch {
      // Error is handled upstream; keep current form state for correction.
    }
  };

  return (
    <form className="card form-card" onSubmit={handleSubmit}>
      <h2 className="card-title">Create Case</h2>
      <div className="form-grid">
        <label className="form-field">
          <span>Title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Missing journalist in District 4"
            required
          />
        </label>
        <label className="form-field">
          <span>Difficulty</span>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as CaseDifficulty)}
          >
            {difficulties.map((item) => (
              <option key={item} value={item}>
                {item.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          <span>Status</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as CaseStatus)}
          >
            {statuses.map((item) => (
              <option key={item} value={item}>
                {item.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field form-field-full">
          <span>Description</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Outline the key beats, main suspects, and investigative hooks."
            rows={4}
            required
          />
        </label>
        <label className="form-field">
          <span>Time Limit (minutes)</span>
          <input
            type="number"
            min={5}
            max={180}
            value={timeLimit}
            onChange={(event) => setTimeLimit(Number(event.target.value))}
          />
        </label>
        <label className="form-field">
          <span>Stress Impact</span>
          <input
            type="number"
            min={0}
            max={100}
            value={stressImpact}
            onChange={(event) => setStressImpact(Number(event.target.value))}
          />
        </label>
        <label className="form-field">
          <span>Reputation Reward</span>
          <input
            type="number"
            min={0}
            max={200}
            value={reputationReward}
            onChange={(event) => setReputationReward(Number(event.target.value))}
          />
        </label>
        <label className="form-field">
          <span>Total Clues</span>
          <input
            type="number"
            min={1}
            max={10}
            value={totalClues}
            onChange={(event) => setTotalClues(Number(event.target.value))}
          />
        </label>
      </div>
      <button className="button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create Case"}
      </button>
    </form>
  );
};

export default CaseForm;
