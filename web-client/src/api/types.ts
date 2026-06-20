export type HealthResponse = {
  status: string;
  service: string;
};

export type AuthConfigResponse = {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  logout_endpoint: string;
  userinfo_endpoint: string;
  jwks_uri: string;
  realm: string;
  clients: Record<string, string>;
};

export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
  exclusion_restrictions?: string[] | null;
};

export type RegisterResponse = {
  id: string;
  username: string;
  email: string;
  message: string;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  expires_in: number;
  refresh_token?: string | null;
  token_type: string;
  scope?: string | null;
};

export type UserProfile = {
  id: string;
  username?: string | null;
  email?: string | null;
  email_verified?: boolean | null;
  first_name?: string | null;
  last_name?: string | null;
};

export type UserPreferences = {
  exclusion_restrictions: string[];
};

export type UpdatePreferencesRequest = {
  exclusion_restrictions?: string[] | null;
};

export type ParsedIngredient = {
  name: string;
  quantity?: number | null;
  unit?: string | null;
  raw_text: string;
};

export type RecommendRequest = {
  query: string;
  top_k?: number;
  available_ingredients?: ParsedIngredient[] | null;
  exclusion_restrictions?: string[] | null;
};

export type ReasoningDetail = {
  positive: string[];
  negative: string[];
};

export type RecipeResult = {
  rank: number;
  id: number;
  title?: string | null;
  summary?: string | null;
  time_minutes?: number | null;
  score: number;
  reasoning?: ReasoningDetail | null;
  directions?: string[] | null;
  inventory_matched?: string[] | null;
  inventory_missing?: string[] | null;
};

export type PipelineStage = {
  name: string;
  status: string;
  latency_ms: number;
};

export type RecommendResponse = {
  results: RecipeResult[];
  stages: PipelineStage[];
};

export type ApiErrorPayload = {
  detail?: unknown;
};
