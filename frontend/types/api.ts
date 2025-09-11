// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Auth Types
export interface User {
  id: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;  // Added for compatibility
  name?: string;       // Added for display purposes
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  organizations?: Organization[];
  current_organization_id?: string;
  current_project_id?: string;
  role?: string;       // Added for team member contexts
  onboarding_completed?: boolean;  // Added for onboarding flow control
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

// Organization Types
export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  created_at: string;
  updated_at: string;
  members?: OrganizationMember[];
  projects?: Project[];
  owner_id: string;
  settings?: OrganizationSettings;
  members_count?: number;
  projects_count?: number;
  is_active?: boolean;  // Added for active status
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  organization_id: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
  user?: User;
}

export interface OrganizationInvitation {
  id: string;
  organization_id: string;
  email: string;
  role: 'admin' | 'member' | 'viewer';
  invited_by: string;
  created_at: string;
  expires_at: string;
  accepted_at?: string;
  status?: 'pending' | 'accepted' | 'expired' | 'cancelled';  // Added for status tracking
}

export interface OrganizationSettings {
  id: string;
  organization_id: string;
  billing_email?: string;
  invoice_details?: Record<string, any>;
  default_project_settings?: Partial<ProjectSettings>;
}

export interface AuditLog {
  id: string;
  organization_id: string;
  user_id: string;
  user?: User;  // Added for populated user data
  action: string;
  resource_type: string;
  resource_id: string;
  details?: Record<string, any>;
  metadata?: Record<string, any>;  // Added for additional metadata
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

// Project Types
export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  url: string;
  organization_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  settings?: ProjectSettings;
  domain?: Domain;
  sites_count?: number;
  team_members_count?: number;
  is_active?: boolean;
  keywords?: string[];  // Added for market simulation
  sites?: Site[];       // Added for sites relationship
}

export interface ProjectSettings {
  id: string;
  project_id: string;
  search_console_enabled: boolean;
  analytics_enabled: boolean;
  pagespeed_enabled: boolean;
  social_media_enabled: boolean;
  crawl_frequency: 'daily' | 'weekly' | 'monthly';
  notification_email?: string;
  webhook_url?: string;
}

// Domain Types
export interface Domain {
  id: string;
  domain: string;
  project_id: string;
  is_verified: boolean;
  verification_method: 'dns' | 'html' | 'meta';
  verification_token: string;
  verified_at?: string;
  created_at: string;
  updated_at: string;
}

// Diagnostic Types
export interface DiagnosticReport {
  id: string;
  project_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  overall_score: number;
  technical_score: number;
  content_score: number;
  ux_score: number;
  issues_count: number;
  warnings_count: number;
  created_at: string;
  completed_at?: string;
  data?: DiagnosticData;
}

export interface DiagnosticData {
  technical_issues: TechnicalIssue[];
  content_issues: ContentIssue[];
  ux_issues: UXIssue[];
  performance_metrics: PerformanceMetrics;
  seo_metrics: SEOMetrics;
}

export interface TechnicalIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affected_pages: string[];
  recommendation: string;
}

export interface ContentIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affected_pages: string[];
  recommendation: string;
}

export interface UXIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affected_pages: string[];
  recommendation: string;
}

export interface PerformanceMetrics {
  page_speed_score: number;
  first_contentful_paint: number;
  largest_contentful_paint: number;
  total_blocking_time: number;
  cumulative_layout_shift: number;
  time_to_interactive: number;
}

export interface SEOMetrics {
  meta_description_coverage: number;
  title_tag_coverage: number;
  h1_coverage: number;
  image_alt_coverage: number;
  internal_links_avg: number;
  external_links_avg: number;
}

// Profitability Types
export interface ProfitabilityData {
  id: string;
  project_id: string;
  period: string;
  revenue: number;
  costs: number;
  profit: number;
  roi: number;
  metrics: ProfitabilityMetrics;
  created_at: string;
}

export interface ProfitabilityMetrics {
  organic_traffic_value: number;
  conversion_value: number;
  ranking_improvements_value: number;
  time_saved_value: number;
  tool_costs: number;
  labor_costs: number;
  opportunity_costs: number;
}

// Market Simulation Types
export interface MarketAnalysis {
  id: string;
  project_id: string;
  keyword: string;
  market_share: number;
  competitor_count: number;
  difficulty_score: number;
  opportunity_score: number;
  competitors: Competitor[];
  trends: MarketTrend[];
  created_at: string;
}

export interface Competitor {
  domain: string;
  market_share: number;
  traffic_estimate: number;
  ranking_keywords: number;
  domain_authority: number;
  strengths: string[];
  weaknesses: string[];
}

export interface MarketTrend {
  date: string;
  search_volume: number;
  competition_level: number;
  trend_direction: 'up' | 'down' | 'stable';
}

// Content Workflow Types
export interface ContentItem {
  id: string;
  project_id: string;
  title: string;
  slug: string;
  status: 'draft' | 'review' | 'published' | 'archived';
  type: 'article' | 'page' | 'landing' | 'blog';
  author_id: string;
  content?: string;
  meta_title?: string;
  meta_description?: string;
  target_keywords: string[];
  seo_score: number;
  readability_score: number;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

// SGE Readiness Types
export interface SGEReadinessReport {
  id: string;
  project_id: string;
  overall_score: number;
  content_score: number;
  technical_score: number;
  authority_score: number;
  recommendations: SGERecommendation[];
  opportunities: SGEOpportunity[];
  created_at: string;
}

export interface SGERecommendation {
  type: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  impact_score: number;
  effort_score: number;
}

export interface SGEOpportunity {
  type: string;
  title: string;
  description: string;
  potential_impact: string;
  implementation_steps: string[];
}

// Knowledge Engine Types
export interface KnowledgeEntry {
  id: string;
  project_id: string;
  title: string;
  category: string;
  tags: string[];
  content: string;
  source?: string;
  insights?: string[];
  related_entries?: string[];
  created_at: string;
  updated_at: string;
}

// Analytics Types
export interface AnalyticsOverview {
  sessions: number;
  users: number;
  pageviews: number;
  bounce_rate: number;
  avg_session_duration: number;
  conversion_rate: number;
  trend_data: TrendData[];
}

export interface TrendData {
  date: string;
  value: number;
  previous_value?: number;
  change_percentage?: number;
}

// Search Console Types
export interface SearchConsoleData {
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  queries: SearchQuery[];
  pages: SearchPage[];
}

export interface SearchQuery {
  query: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface SearchPage {
  page: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

// Subscription Types
export interface Subscription {
  id: string;
  user_id: string;
  organization_id: string;
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  status: 'active' | 'canceled' | 'past_due' | 'trial';
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_end?: string;
  features: string[];
}

// Notification Types
export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  action_url?: string;
  created_at: string;
}

// Activity Types
export interface Activity {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

// Sites Types (NEW)
export interface Site {
  id: string;
  url: string;
  name?: string;
  description?: string;
  project_id?: string;
  project?: Project;
  verified: boolean;
  is_verified?: boolean;
  last_crawled?: string;
  crawl_status?: 'pending' | 'running' | 'completed' | 'failed';
  pages_count?: number;
  issues_count?: number;
  created_at: string;
  updated_at: string;
  is_active?: boolean;
  crawl_enabled?: boolean;
  crawl_frequency?: 'daily' | 'weekly' | 'monthly';
}

export interface SiteHealth {
  id: string;
  site_id: string;
  overall_score: number;
  pages_indexed?: number;
  last_crawl_date?: string;
  cwv_passing?: number;
  seo_issues?: number;
}

export interface CrawlResult {
  id: string;
  site_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  pages_crawled: number;
  issues_found: number;
  started_at: string;
  completed_at?: string;
  error?: string;
}

// OAuth Integration Types (NEW)
export interface OAuthConnection {
  id: string;
  user_id: string;
  provider: 'google' | 'facebook' | 'linkedin';
  access_token?: string;
  refresh_token?: string;
  expires_at?: string;
  scopes: string[];
  connected_at: string;
  last_refreshed?: string;
  status: 'active' | 'expired' | 'revoked';
}

// Health & Performance Types (NEW)
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  timestamp: string;
  services: ServiceHealth[];
}

export interface ServiceHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  response_time_ms?: number;
  error?: string;
  last_check: string;
}

export interface DatabaseStats {
  total_connections: number;
  active_connections: number;
  idle_connections: number;
  total_queries: number;
  slow_queries: number;
  database_size_mb: number;
  tables: TableStats[];
}

export interface TableStats {
  name: string;
  row_count: number;
  size_mb: number;
  index_size_mb: number;
}

export interface ApiPerformanceMetrics {
  endpoint: string;
  method: string;
  count: number;
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
  error_rate: number;
  last_hour_stats: HourlyStats[];
}

export interface HourlyStats {
  hour: string;
  requests: number;
  errors: number;
  avg_response_time_ms: number;
}

// Cache Management Types (NEW)
export interface CacheStats {
  total_keys: number;
  memory_used_mb: number;
  memory_available_mb: number;
  hit_rate: number;
  miss_rate: number;
  eviction_count: number;
  keys_by_pattern: CacheKeyPattern[];
}

export interface CacheKeyPattern {
  pattern: string;
  count: number;
  avg_size_kb: number;
  avg_ttl_seconds: number;
}

// Background Tasks Types (NEW)
export interface BackgroundTask {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  metadata?: Record<string, any>;
}

// Settings Types (NEW)
export interface UserProfile {
  id: string;
  user_id: string;
  full_name: string;
  avatar_url?: string;
  timezone?: string;
  language?: string;
  bio?: string;
  company?: string;
  job_title?: string;
  phone?: string;
  updated_at: string;
}

export interface SecuritySettings {
  two_factor_enabled: boolean;
  two_factor_method?: 'totp' | 'sms' | 'email';
  password_last_changed: string;
  login_notifications: boolean;
  api_access_enabled: boolean;
}

export interface TeamMember {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  name?: string; // Added for compatibility
  role: 'owner' | 'admin' | 'developer' | 'analyst' | 'viewer';
  joined_at: string;
  last_active?: string;
  permissions: string[];
}

export interface Integration {
  id: string;
  type: 'slack' | 'teams' | 'webhook' | 'zapier' | 'datadog';
  name: string;
  config: Record<string, any>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_sync?: string;
  error?: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  expires_at?: string;
  last_used?: string;
  created_at: string;
}

export interface NotificationPreference {
  id: string;
  type: string;
  channel: 'email' | 'in_app' | 'push' | 'sms';
  enabled: boolean;
  frequency?: 'realtime' | 'daily' | 'weekly';
}

export interface UsageStats {
  period: string;
  api_calls: number;
  storage_mb: number;
  bandwidth_mb: number;
  users_count: number;
  projects_count: number;
  limits: UsageLimits;
}

export interface UsageLimits {
  max_api_calls: number;
  max_storage_mb: number;
  max_bandwidth_mb: number;
  max_users: number;
  max_projects: number;
}

// Webhook Types (NEW)
export interface Webhook {
  id: string;
  project_id: string;
  url: string;
  events: string[];
  enabled: boolean;
  secret?: string;
  created_at: string;
  updated_at: string;
  last_triggered?: string;
  failure_count: number;
}

// Session Types (NEW)
export interface UserSession {
  id: string;
  user_id: string;
  token_prefix: string;
  ip_address: string;
  user_agent: string;
  location?: string;
  created_at: string;
  last_active: string;
  expires_at: string;
}