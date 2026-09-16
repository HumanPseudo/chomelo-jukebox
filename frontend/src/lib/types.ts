export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserOut {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  display_name: string;
}

export interface ProfileOut {
  user_id: number;
  display_name: string;
  avatar_url: string | null;
  bio: string;
  xp: number;
  level: number;
  created_at: string;
  tracks_added: number;
  tracks_played: number;
  votes_cast: number;
  polls_created: number;
  poll_votes_cast: number;
}

export interface ListenHistoryItem {
  track_id: string;
  title: string;
  artist: string;
  thumbnail_url: string | null;
  jukebox_name: string;
  played_at: string;
}

export type Role = "OWNER" | "ADMIN" | "MODERATOR" | "MEMBER" | "GUEST";

export const ROLE_RANK: Record<Role, number> = {
  OWNER: 100,
  ADMIN: 90,
  MODERATOR: 70,
  MEMBER: 50,
  GUEST: 30,
};

export function roleAtLeast(role: Role, min: Role): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[min];
}

export interface JukeboxOut {
  id: number;
  name: string;
  description: string;
  owner_id: number;
  invite_code: string;
  is_active: boolean;
  created_at: string;
  role: Role;
  member_count: number;
}

export interface MemberOut {
  user_id: number;
  role: Role;
  display_name: string;
}

export interface TrackInfo {
  provider: string;
  track_id: string;
  title: string;
  artist: string;
  duration_seconds: number | null;
  thumbnail_url: string | null;
}

export interface QueueItemOut {
  id: number;
  track_id: string;
  title: string;
  artist: string;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  added_by: number;
  status: "QUEUED" | "PLAYING" | "PLAYED" | "SKIPPED";
  position: number | null;
  created_at: string;
  score: number;
  voted_by_me: boolean;
}

export interface PlayerStateOut {
  is_playing: boolean;
  position_ms: number;
  current_item_id: number | null;
}

export interface QueueOut {
  items: QueueItemOut[];
  player: PlayerStateOut;
}

export interface PollOptionOut {
  id: number;
  text: string;
  votes: number;
}

export interface PollOut {
  id: number;
  question: string;
  status: "OPEN" | "CLOSED";
  closes_at: string | null;
  created_at: string;
  created_by: number;
  options: PollOptionOut[];
  my_option_id: number | null;
  total_votes: number;
}

export interface MyAttemptOut {
  selected: string;
  correct: boolean;
  points: number;
}

export interface RoundOut {
  id: number;
  jukebox_id: number;
  game_key: string;
  game_name: string;
  status: "OPEN" | "FINISHED";
  track_id: string;
  artist: string;
  thumbnail_url: string | null;
  options: string[];
  starts_at: string;
  expires_at: string;
  finished_at: string | null;
  created_by: number;
  my_attempt: MyAttemptOut | null;
  correct_title: string | null;
}

export interface AttemptOut {
  round_id: number;
  selected: string;
  correct: boolean;
  points: number;
  correct_title: string | null;
  round_status: string;
}

export interface WalletTransactionOut {
  id: number;
  kind: string;
  amount: number;
  description: string;
  created_at: string;
}

export interface WalletOut {
  credits: number;
  transactions: WalletTransactionOut[];
}

export interface WsEvent {
  event: string;
  jukebox_id?: number;
  data?: Record<string, unknown>;
}
