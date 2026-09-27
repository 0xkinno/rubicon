/**
 * lib/api.ts: Typed API client for Rubicon backend
 */

const BASE_URL = process.env.NEXT_PUBLIC_RUBICON_API_URL || 'http://localhost:8000'

export interface StatusResponse {
  status: string
  decisions_total: number
  blocked: number
  allowed: number
  receipts_total: number
  public_key_loaded: boolean
}

export interface Decision {
  ts: number
  session_id: string
  tool: string
  action_id: string
  classification: string
  domains: string[]
  decision: 'ALLOW' | 'BLOCK'
  reason: string
  permit_id?: string
}

export interface ReceiptSummary {
  id: string
  session_id: string
  action_id: string
  decision: string
  domain_results: Array<{ domain: string; result: string }>
  signature_present: boolean
}

export interface ReceiptDetail extends ReceiptSummary {
  receipt_version: string
  policy_version: string
  verifier_version: string
  pre_manifest_sha256: string
  post_action_manifest_sha256: string
  post_rollback_manifest_sha256: string
  observability: Record<string, string>
  limitations: string[]
  signature: string
}

export interface CampaignResult {
  status: string
  drills?: DrillResult[]
  metrics?: CampaignMetrics
}

export interface DrillResult {
  drill_id: string
  scenario: string
  baseline_arm: string
  rubicon_arm: string
  action_digest: string
  pre_state_sha256: string
  post_action_sha256: string
  post_rollback_sha256: string
  policy_decision: string
  observed_result: string
  verifier_verdict: string
  pass: boolean
}

export interface CampaignMetrics {
  dangerous_actions_blocked: number
  legitimate_actions_allowed: number
  post_rollback_residual_detected: number
  rollback_fidelity: number
  coverage_prediction_accuracy: number
  residual_detection_rate: number
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

export const api = {
  health: () => fetchApi<{ status: string }>('/api/health'),
  status: () => fetchApi<StatusResponse>('/api/status'),
  decisions: (limit = 50) => fetchApi<{ decisions: Decision[] }>(`/api/decisions?limit=${limit}`),
  receipts: () => fetchApi<{ receipts: ReceiptSummary[] }>('/api/receipts'),
  receipt: (id: string) => fetchApi<ReceiptDetail>(`/api/receipts/${id}`),
  pendingPermits: () => fetchApi<{ permits: unknown[] }>('/api/permits/pending'),
  campaign: () => fetchApi<CampaignResult>('/api/campaign'),
  classify: (tool: string, input: Record<string, unknown>, sessionId = 'preview') =>
    fetchApi<{ classification: string; vector: unknown }>('/api/classify', {
      method: 'POST',
      body: JSON.stringify({ tool, input, session_id: sessionId }),
    }),
}
