// Contract types — authoritative source: frontend-backend-contract.md §3

export type Category = "transport" | "waste" | "nature" | "reuse" | "community";
export type SubmissionStatus = "approved" | "rejected" | "error" | "pending";

export interface User {
  id: number;
  email: string;
  display_name: string;
  points_total: number;
  created_at: string;
}

export interface ChallengeSummary {
  id: number;
  slug: string;
  title: string;
  tagline: string;
  points: number;
  co2_saved_grams: number;
  co2_note: string;
  category: Category;
  icon: string;
  cooldown_hours: number;
  times_completed: number;
  can_submit: boolean;
  cooldown_ends_at: string | null;
}

export interface ChallengeDetail extends ChallengeSummary {
  description: string;
  instructions: string;
  evidence_requirements: string;
}

export interface Badge {
  key: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  current: number;
  target: number;
}

export interface Profile {
  display_name: string;
  email: string;
  points_total: number;
  submissions_total: number;
  submissions_approved: number;
  submissions_rejected: number;
  challenges_completed: number;
  co2_saved_grams: number;
  rank: number;
  total_participants: number;
  badges: Badge[];
  member_since: string;
}

export interface Submission {
  id: number;
  challenge: { id: number; slug: string; title: string; points: number; icon: string };
  status: SubmissionStatus;
  points_awarded: number;
  co2_saved_grams: number;
  verification: {
    approved: boolean | null;
    confidence: number | null;
    reason: string | null;
    model: string | null;
  };
  image_url: string;
  created_at: string;
  verified_at: string | null;
}

export interface SubmissionResult {
  submission: Submission;
  profile: Profile;
  new_badges: Badge[];
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  display_name: string;
  points_total: number;
  challenges_completed: number;
  is_current_user: boolean;
}

export interface Leaderboard {
  entries: LeaderboardEntry[];
  total_participants: number;
  current_user_rank: number;
}

export interface Meta {
  name: string;
  version: string;
  verification_provider: string;
  verification_disclaimer: string;
  environmental_disclaimer: string;
  api_docs: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
}
