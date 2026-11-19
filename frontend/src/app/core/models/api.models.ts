export interface AgentSource {
  chunk_id: number;
  document_id: number;
  position: number;
  similarity: number;
  content: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
}

export interface AgentRequest {
  question: string;
  thread_id?: string;
  limit?: number;
  min_similarity?: number;
  user_id?: string;
}

export interface AgentResumeRequest {
  thread_id: string;
  approved: boolean;
  note?: string;
}

export interface AgentResponse {
  thread_id: string;

  status: 'completed' | 'interrupted' | 'rejected';

  question?: string;
  answer?: string;

  route?: 'knowledge' | 'system';

  handled_by?: 'knowledge' | 'system';

  tool_used?: string;

  sources: AgentSource[];

  interrupt?: Record<string, unknown>;
}

/* ------------------------------------------------------------------ */
/* Recommendations                                                     */
/* ------------------------------------------------------------------ */

export interface RecommendationItem {
  document_id: number;
  filename: string;
  score: number;
  semantic_score: number;
  behavioural_score: number;
  popularity_score: number;
  seen: boolean;
  reason: string;
  preview: string;
  chunk_count: number;
}

export interface RecommendationResponse {
  user_id: string;
  strategy: 'personalised' | 'cold_start';
  interaction_count: number;
  generated_at: string;
  items: RecommendationItem[];
}

export interface RecommendationFeedbackRequest {
  user_id: string;
  document_id: number;
  relevant: boolean;
  note?: string;
}

export interface RecommendationEvent {
  id: number;
  event_type: string;
  document_id: number | null;
  query: string | null;
  relevance: number | null;
  created_at: string;
}

export interface RecommendationHistory {
  user_id: string;
  count: number;
  events: RecommendationEvent[];
}

/* ------------------------------------------------------------------ */
/* Planning agent                                                      */
/* ------------------------------------------------------------------ */

export interface PlanRequest {
  task: string;
  user_id?: string;
  limit?: number;
  min_similarity?: number;
  max_revisions?: number;
}

export interface PlanResumeRequest {
  thread_id: string;
  approved: boolean;
  note?: string;
}

export interface PlanStep {
  id: number;
  title: string;
  action: 'search_knowledge' | 'analyze' | 'draft';
  query: string;
  status: string | null;
  evidence_count: number;
}

export interface PlanEvidence {
  step_id: number;
  document_id: number;
  position: number;
  similarity: number;
  content: string;
}

export interface PlanInterrupt {
  id: string;
  value: {
    action: string;
    message: string;
    plan_summary: string;
    draft: string;
    verification_passed: boolean;
    confidence: number;
    issues: string[];
    critique: string;
    revision_count: number;
  };
}

export interface PlanResponse {
  thread_id: string;
  status: 'completed' | 'interrupted' | 'rejected';
  task: string;
  plan_summary: string;
  plan_steps: PlanStep[];
  dependencies: string[];
  risks: string[];
  evidence: PlanEvidence[];
  draft: string | null;
  critique: string | null;
  issues: string[];
  confidence: number | null;
  verification_passed: boolean | null;
  revision_count: number;
  answer: string | null;
  approval: { approved?: boolean; note?: string } | null;
  interrupt: PlanInterrupt | null;
}

/* ------------------------------------------------------------------ */
/* Evaluation                                                          */
/* ------------------------------------------------------------------ */

export interface EvaluationDataset {
  name: string;
  case_count: number;
  categories: string[];
}

export interface EvaluationPipelineSummary {
  name: string;
  label: string;
  cases: number;
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  context_recall: number;
  pass_rate: number;
  abstention_accuracy: number | null;
  avg_latency_ms: number;
  total_tokens: number;
  failures: number;
  composite_score: number;
}

export interface EvaluationComparison {
  winner: string | null;
  baseline?: string;
  candidate?: string;
  deltas: Record<string, number>;
}

export interface EvaluationSummary {
  dataset: string;
  case_count: number;
  metrics_are_proxies: boolean;
  pipelines: EvaluationPipelineSummary[];
  comparison: EvaluationComparison;
}

export interface EvaluationRun {
  id: number;
  dataset: string;
  status: 'running' | 'completed' | 'failed';
  case_count: number;
  pipelines: Array<{ name: string; label: string }> | null;
  summary: EvaluationSummary | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface EvaluationCase {
  id: number;
  pipeline: string;
  question: string;
  expected_answer: string | null;
  expected_document_ids: number[] | null;
  answer: string | null;
  retrieved_document_ids: number[] | null;
  metrics: Record<string, number | boolean | null> | null;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  passed: boolean;
  error: string | null;
}

export interface EvaluationRunDetail {
  run: EvaluationRun;
  cases: EvaluationCase[];
}

/* ------------------------------------------------------------------ */
/* Observability                                                       */
/* ------------------------------------------------------------------ */

export interface ObservabilityEndpoint {
  endpoint: string;
  requests: number;
  failures: number;
  avg_latency_ms: number;
  tokens: number;
}

export interface ObservabilityRequest {
  endpoint: string;
  pipeline: string;
  question: string | null;
  route: string | null;
  latency_ms: number;
  total_tokens: number;
  success: boolean;
  created_at: string;
  model?: string | null;
  error?: string | null;
}

export interface FailedQuery {
  endpoint: string;
  question: string | null;
  route: string | null;
  error: string | null;
  created_at: string;
}

export interface ObservabilityOverview {
  window_hours: number;
  model: string;
  provider: string;
  requests: number;
  requests_all_time: number;
  successes: number;
  failures: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  tokens_are_estimated: boolean;
  usage_source: 'provider' | 'estimated' | 'mixed';
  endpoints: ObservabilityEndpoint[];
  failed_queries: FailedQuery[];
  recent_requests: ObservabilityRequest[];
}

export interface HealthReadyResponse {
  status: string;
  database: string;
  cache: string;
}
