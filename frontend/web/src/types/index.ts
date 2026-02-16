// ── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  family_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Family ───────────────────────────────────────────────────────────────────

export interface Family {
  id: string;
  name: string;
  timezone: string;
  settings: Record<string, unknown>;
  created_at: string;
}

export interface FamilyUpdate {
  name?: string;
  timezone?: string;
  settings?: Record<string, unknown>;
}

// ── User / Children ──────────────────────────────────────────────────────────

export interface User {
  id: string;
  family_id: string;
  name: string;
  role: 'parent' | 'child';
  email?: string | null;
  avatar_url?: string | null;
  age?: number | null;
  created_at: string;
}

export interface ChildCreate {
  name: string;
  age?: number | null;
  avatar_url?: string | null;
  pin?: string | null;
}

export interface ChildUpdate {
  name?: string;
  age?: number | null;
  avatar_url?: string | null;
}

// ── Device ───────────────────────────────────────────────────────────────────

export interface Device {
  id: string;
  child_id: string;
  name: string;
  type: string;
  device_identifier: string;
  status: string;
  last_seen?: string | null;
  created_at: string;
}

export interface DeviceCreate {
  name: string;
  type: string;
  device_identifier: string;
}

export interface DeviceCoupling {
  id: string;
  child_id: string;
  device_ids: string[];
  shared_budget: boolean;
  created_at: string;
}

// ── App Group ────────────────────────────────────────────────────────────────

export interface AppGroupApp {
  id: string;
  app_name: string;
  app_package?: string | null;
  app_executable?: string | null;
  platform: string;
}

export interface AppGroup {
  id: string;
  child_id: string;
  name: string;
  icon?: string | null;
  color?: string | null;
  category: string;
  risk_level: string;
  always_allowed: boolean;
  tan_allowed: boolean;
  max_tan_bonus_per_day?: number | null;
  apps: AppGroupApp[];
  created_at: string;
}

export interface AppGroupCreate {
  name: string;
  icon?: string | null;
  color?: string | null;
  category: string;
  risk_level?: string;
  always_allowed?: boolean;
  tan_allowed?: boolean;
  max_tan_bonus_per_day?: number | null;
}

export interface AppGroupUpdate {
  name?: string;
  icon?: string | null;
  color?: string | null;
  category?: string;
  risk_level?: string;
  always_allowed?: boolean;
  tan_allowed?: boolean;
  max_tan_bonus_per_day?: number | null;
}

export interface AppCreate {
  app_name: string;
  app_package?: string | null;
  app_executable?: string | null;
  platform: string;
}

// ── Time Rule ────────────────────────────────────────────────────────────────

export interface TimeWindow {
  start: string; // "HH:MM"
  end: string;   // "HH:MM"
  note?: string | null;
}

export interface GroupLimit {
  group_id: string;
  max_minutes: number;
}

export interface TimeRule {
  id: string;
  child_id: string;
  name: string;
  target_type: string;
  target_id?: string | null;
  day_types: string[];
  time_windows: TimeWindow[];
  daily_limit_minutes?: number | null;
  group_limits: GroupLimit[];
  priority: number;
  active: boolean;
  valid_from?: string | null;
  valid_until?: string | null;
  created_at: string;
}

export interface TimeRuleCreate {
  name: string;
  target_type: string;
  target_id?: string | null;
  day_types?: string[];
  time_windows: TimeWindow[];
  daily_limit_minutes?: number | null;
  group_limits?: GroupLimit[];
  priority?: number;
  valid_from?: string | null;
  valid_until?: string | null;
}

export interface TimeRuleUpdate {
  name?: string;
  day_types?: string[];
  time_windows?: TimeWindow[];
  daily_limit_minutes?: number | null;
  group_limits?: GroupLimit[];
  priority?: number;
  active?: boolean;
  valid_from?: string | null;
  valid_until?: string | null;
}

// ── TAN ──────────────────────────────────────────────────────────────────────

export interface TAN {
  id: string;
  child_id: string;
  code: string;
  type: string;
  scope_groups?: string[] | null;
  scope_devices?: string[] | null;
  value_minutes?: number | null;
  value_unlock_until?: string | null;
  expires_at: string;
  single_use: boolean;
  source?: string | null;
  status: string;
  redeemed_at?: string | null;
  created_at: string;
}

export interface TANCreate {
  type: string;
  scope_groups?: string[] | null;
  scope_devices?: string[] | null;
  value_minutes?: number | null;
  value_unlock_until?: string | null;
  expires_at?: string | null;
  single_use?: boolean;
}

export interface TANRedeemRequest {
  code: string;
}

// ── Quest ────────────────────────────────────────────────────────────────────

export interface QuestTemplate {
  id: string;
  family_id: string;
  name: string;
  description?: string | null;
  category: string;
  reward_minutes: number;
  tan_groups?: string[] | null;
  proof_type: string;
  ai_verify: boolean;
  ai_prompt?: string | null;
  recurrence: string;
  auto_detect_app?: string | null;
  auto_detect_minutes?: number | null;
  streak_threshold?: number | null;
  subject?: string | null;
  estimated_minutes?: number | null;
  difficulty?: string | null;
  checklist_items?: string[] | null;
  active: boolean;
  created_at: string;
}

export interface QuestTemplateCreate {
  name: string;
  description?: string | null;
  category: string;
  reward_minutes: number;
  tan_groups?: string[] | null;
  proof_type: string;
  ai_verify?: boolean;
  ai_prompt?: string | null;
  recurrence: string;
  auto_detect_app?: string | null;
  auto_detect_minutes?: number | null;
  streak_threshold?: number | null;
  subject?: string | null;
  estimated_minutes?: number | null;
  difficulty?: string | null;
  checklist_items?: string[] | null;
}

export interface QuestTemplateUpdate {
  name?: string;
  description?: string | null;
  category?: string;
  reward_minutes?: number;
  proof_type?: string;
  ai_verify?: boolean;
  ai_prompt?: string | null;
  recurrence?: string;
  auto_detect_app?: string | null;
  auto_detect_minutes?: number | null;
  streak_threshold?: number | null;
  subject?: string | null;
  estimated_minutes?: number | null;
  difficulty?: string | null;
  checklist_items?: string[] | null;
  active?: boolean;
}

export interface QuestInstance {
  id: string;
  template_id: string;
  child_id: string;
  status: string;
  claimed_at?: string | null;
  proof_url?: string | null;
  ai_result?: Record<string, unknown> | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  generated_tan_id?: string | null;
  created_at: string;
}

export interface QuestSubmitProof {
  proof_type: string;
  proof_url: string;
}

export interface QuestReview {
  approved: boolean;
  feedback?: string | null;
}

// ── Day Type ─────────────────────────────────────────────────────────────────

export interface DayTypeOverride {
  id: string;
  family_id: string;
  date: string;
  day_type: string;
  label?: string | null;
  source: string;
}

export interface DayTypeOverrideCreate {
  date: string;
  day_type: string;
  label?: string | null;
}

// ── LLM / AI ────────────────────────────────────────────────────────────────

export interface VerifyProofRequest {
  quest_instance_id: string;
}

export interface VerifyProofResponse {
  approved: boolean;
  confidence: number;
  feedback: string;
  auto_approved: boolean;
}

export interface ParseRuleRequest {
  text: string;
  child_id?: string | null;
}

export interface ParseRuleResponse {
  success: boolean;
  rule?: Record<string, unknown> | null;
  error?: string | null;
}

export interface WeeklyReportResponse {
  child_id: string;
  child_name: string;
  report: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  response: string;
}

// ── Usage Rewards ───────────────────────────────────────────────────────────

export interface UsageRewardRule {
  id: string;
  child_id: string;
  name: string;
  trigger_type: 'daily_under' | 'streak_under' | 'group_free';
  threshold_minutes: number;
  target_group_id: string | null;
  streak_days: number | null;
  reward_minutes: number;
  reward_group_ids: string[] | null;
  active: boolean;
  created_at: string;
}

export interface UsageRewardRuleCreate {
  name: string;
  trigger_type: string;
  threshold_minutes: number;
  target_group_id?: string | null;
  streak_days?: number | null;
  reward_minutes: number;
  reward_group_ids?: string[] | null;
}

export interface UsageRewardRuleUpdate {
  name?: string;
  trigger_type?: string;
  threshold_minutes?: number;
  target_group_id?: string | null;
  streak_days?: number | null;
  reward_minutes?: number;
  reward_group_ids?: string[] | null;
  active?: boolean;
}

export interface UsageRewardLog {
  id: string;
  rule_id: string;
  child_id: string;
  evaluated_date: string;
  usage_minutes: number;
  threshold_minutes: number;
  rewarded: boolean;
  generated_tan_id: string | null;
  created_at: string;
}

// ── Invitation ──────────────────────────────────────────────────────────────

export interface FamilyInvitation {
  id: string;
  family_id: string;
  code: string;
  role: string;
  created_by: string;
  expires_at: string;
  used_by: string | null;
  used_at: string | null;
  created_at: string;
}

export interface InvitationCreate {
  role?: string;
}

export interface RegisterWithInvitationRequest {
  email: string;
  password: string;
  password_confirm: string;
  name: string;
  invitation_code: string;
}

export interface ProfileUpdate {
  name?: string;
  email?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface GroupUsage {
  app_group_id: string | null;
  group_name: string;
  minutes: number;
  percentage: number;
}

export interface DailySummary {
  date: string;
  total_minutes: number;
  group_breakdown: GroupUsage[];
  quests_completed: number;
  tans_redeemed: number;
  blocked_attempts: number;
}

export interface HeatmapEntry {
  hour: number;
  day: number;
  minutes: number;
}

export interface WeeklyTrend {
  week_start: string;
  total_minutes: number;
  quests_completed: number;
  tans_redeemed: number;
}

export interface ChildDashboardStats {
  child_id: string;
  child_name: string;
  usage_today_minutes: number;
  daily_limit_minutes: number | null;
  active_tans: number;
  quests_completed_today: number;
  current_streak: number;
  devices_online: number;
  top_group: string | null;
}

export interface FamilyDashboardStats {
  total_children: number;
  total_active_rules: number;
  tans_today: number;
  total_usage_today_minutes: number;
}

export interface AnalyticsResponse {
  child_id: string;
  child_name: string;
  period: string;
  daily_summaries: DailySummary[];
  heatmap: HeatmapEntry[];
  trends: WeeklyTrend[];
  group_breakdown: GroupUsage[];
}
