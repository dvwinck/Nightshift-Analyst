export type User = {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
};

export type CaseStatus = "pending" | "in_progress" | "completed" | "failed";

export type CaseDifficulty = "easy" | "medium" | "hard" | "extreme";

export type Case = {
  id: string;
  user_id: string;
  title: string;
  description: string;
  difficulty: CaseDifficulty;
  status: CaseStatus;
  time_limit_minutes: number;
  stress_impact: number;
  reputation_reward: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  evidence_data: string | null;
  clues_found: number;
  total_clues: number;
};

export type CaseCreatePayload = {
  user_id: string;
  title: string;
  description: string;
  difficulty: CaseDifficulty;
  status?: CaseStatus;
  time_limit_minutes?: number;
  stress_impact?: number;
  reputation_reward?: number;
  evidence_data?: string | null;
  clues_found?: number;
  total_clues?: number;
};

export type CaseUpdatePayload = Partial<Pick<Case, "status" | "started_at" | "completed_at" | "evidence_data" | "clues_found">>;
