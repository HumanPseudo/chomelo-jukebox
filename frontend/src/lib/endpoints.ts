import { api, tokens } from "./api";
import type {
  AttemptOut,
  CheckoutOut,
  JukeboxOut,
  ListenHistoryItem,
  MemberOut,
  PaymentOut,
  PollOut,
  ProfileOut,
  QueueItemOut,
  QueueOut,
  ResolvedTrack,
  RoundOut,
  TokenResponse,
  TrackInfo,
  UserOut,
  WalletOut,
} from "./types";

export const auth = {
  register: (email: string, password: string, display_name?: string) =>
    api.post<TokenResponse>("/auth/register", { email, password, display_name }, { auth: false }),
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }, { auth: false }),
  logout: () => tokens.clear(),
};

export const users = {
  me: () => api.get<UserOut>("/users/me"),
  profile: () => api.get<ProfileOut>("/users/me/profile"),
  updateProfile: (patch: { display_name?: string; bio?: string; avatar_url?: string }) =>
    api.patch<ProfileOut>("/users/me/profile", patch),
  history: (limit = 20) => api.get<ListenHistoryItem[]>("/users/me/listen-history", { limit }),
  wallet: () => api.get<WalletOut>("/users/me/wallet"),
};

export const jukeboxes = {
  list: () => api.get<JukeboxOut[]>("/jukeboxes"),
  create: (name: string, description = "") =>
    api.post<JukeboxOut>("/jukeboxes", { name, description }),
  join: (invite_code: string) => api.post<JukeboxOut>("/jukeboxes/join", { invite_code }),
  get: (id: number) => api.get<JukeboxOut>(`/jukeboxes/${id}`),
  members: (id: number) => api.get<MemberOut[]>(`/jukeboxes/${id}/members`),
  setRole: (id: number, userId: number, role: string) =>
    api.patch<MemberOut>(`/jukeboxes/${id}/members/${userId}`, { role }),
  removeMember: (id: number, userId: number) =>
    api.delete(`/jukeboxes/${id}/members/${userId}`),
  invite: (id: number) => api.post<{ invite_code: string }>(`/jukeboxes/${id}/invite`),
};

export const music = {
  search: (q: string) => api.get<TrackInfo[]>("/music/search", { q }),
  resolveStream: (trackId: string) =>
    api.get<ResolvedTrack>(`/music/tracks/${trackId}/stream`),
};

export const queue = {
  get: (jukeboxId: number) => api.get<QueueOut>(`/jukeboxes/${jukeboxId}/queue`),
  add: (jukeboxId: number, track_id: string) =>
    api.post(`/jukeboxes/${jukeboxId}/queue`, { track_id }),
  remove: (jukeboxId: number, itemId: number) =>
    api.delete(`/jukeboxes/${jukeboxId}/queue/${itemId}`),
  move: (jukeboxId: number, itemId: number, position: number) =>
    api.patch(`/jukeboxes/${jukeboxId}/queue/${itemId}/move`, { position }),
  vote: (jukeboxId: number, itemId: number) =>
    api.post(`/jukeboxes/${jukeboxId}/queue/${itemId}/vote`),
  unvote: (jukeboxId: number, itemId: number) =>
    api.delete(`/jukeboxes/${jukeboxId}/queue/${itemId}/vote`),
  boost: (jukeboxId: number, itemId: number, credits: number) =>
    api.post<QueueItemOut>(`/jukeboxes/${jukeboxId}/queue/${itemId}/boost`, { credits }),
  history: (jukeboxId: number) => api.get(`/jukeboxes/${jukeboxId}/history`),
  player: {
    play: (jukeboxId: number) => api.post(`/jukeboxes/${jukeboxId}/player/play`),
    pause: (jukeboxId: number) => api.post(`/jukeboxes/${jukeboxId}/player/pause`),
    resume: (jukeboxId: number) => api.post(`/jukeboxes/${jukeboxId}/player/resume`),
    next: (jukeboxId: number) => api.post(`/jukeboxes/${jukeboxId}/player/next`),
    seek: (jukeboxId: number, position_ms: number) =>
      api.post(`/jukeboxes/${jukeboxId}/player/seek`, { position_ms }),
  },
};

export const polls = {
  list: (jukeboxId: number, status?: "OPEN" | "CLOSED") =>
    api.get<PollOut[]>(`/jukeboxes/${jukeboxId}/polls`, { status }),
  create: (jukeboxId: number, question: string, options: string[], closes_at?: string) =>
    api.post<PollOut>(`/jukeboxes/${jukeboxId}/polls`, { question, options, closes_at }),
  vote: (jukeboxId: number, pollId: number, option_id: number) =>
    api.post(`/jukeboxes/${jukeboxId}/polls/${pollId}/vote`, { option_id }),
  close: (jukeboxId: number, pollId: number) =>
    api.post<PollOut>(`/jukeboxes/${jukeboxId}/polls/${pollId}/close`),
  remove: (jukeboxId: number, pollId: number) =>
    api.delete(`/jukeboxes/${jukeboxId}/polls/${pollId}`),
};

export const payments = {
  checkout: (credits: number, currency = "eur") =>
    api.post<CheckoutOut>("/users/me/payments/checkout", { credits, currency }),
  list: () => api.get<PaymentOut[]>("/users/me/payments"),
};

export const games = {
  list: (jukeboxId: number, gameKey: string, status?: string) =>
    api.get<RoundOut[]>(`/jukeboxes/${jukeboxId}/games/${gameKey}/rounds`, { status }),
  start: (jukeboxId: number, gameKey: string, duration_seconds = 60) =>
    api.post<RoundOut>(`/jukeboxes/${jukeboxId}/games/${gameKey}/rounds`, { duration_seconds }),
  get: (jukeboxId: number, gameKey: string, roundId: number) =>
    api.get<RoundOut>(`/jukeboxes/${jukeboxId}/games/${gameKey}/rounds/${roundId}`),
  answer: (jukeboxId: number, gameKey: string, roundId: number, title: string) =>
    api.post<AttemptOut>(`/jukeboxes/${jukeboxId}/games/${gameKey}/rounds/${roundId}/answer`, {
      title,
    }),
};
