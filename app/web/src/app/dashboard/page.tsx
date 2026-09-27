'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { api, type StatusResponse, type Decision, type ReceiptSummary, type TelemetryStatus } from '@/lib/api'
import { ThemeToggle } from '@/components/ThemeToggle'

// ── Verdict Badge (Consistent Theme Palette) ───────────────────────────────

function VerdictChip({ verdict }: { verdict: string }) {
  const map: Record<string, string> = {
    RESTORED: 'chip-restored',
    ALLOW: 'chip-restored',
    COVERED_REVERSIBLE: 'chip-restored',
    PARTIAL: 'chip-partial',
    BOUNDARY_REQUIRES_PERMIT: 'chip-partial',
    BREACH: 'chip-breach',
    BLOCK: 'chip-breach',
    OUTSIDE_ROLLBACK: 'chip-breach',
    UNKNOWN: 'chip-unknown',
    UNKNOWN_EFFECT: 'chip-unknown',
  }
  return (
    <span className={`chip ${map[verdict] || 'chip-unknown'}`}>
      {verdict}
    </span>
  )
}

// ── Metric Card ───────────────────────────────────────────────────────────

function MetricCard({
  value,
  label,
  sub,
  accent = false,
}: {
  value: string | number
  label: string
  sub?: string
  accent?: boolean
}) {
  return (
    <div className="rubicon-card p-5">
      <div
        className="text-3xl font-mono font-bold tabular-nums mb-1"
        style={{
          color: accent ? 'var(--rubicon-threshold)' : 'var(--text-ink)',
          textShadow: accent ? '0 0 15px rgba(220, 20, 60, 0.25)' : 'none',
        }}
      >
        {value}
      </div>
      <div className="text-xs font-semibold tracking-wide uppercase opacity-75" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
      {sub && <div className="text-[11px] font-mono mt-1 opacity-60" style={{ color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

// ── Decision Row ──────────────────────────────────────────────────────────

function DecisionRow({ d }: { d: Decision }) {
  const ts = new Date(d.ts * 1000).toLocaleTimeString()
  return (
    <div className="flex items-start gap-4 py-3.5 border-b last:border-0" style={{ borderColor: 'var(--border-line)' }}>
      <div className="flex-shrink-0 w-16 text-xs font-mono opacity-50 pt-0.5" style={{ color: 'var(--text-muted)' }}>
        {ts}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <VerdictChip verdict={d.decision} />
          <span className="font-mono text-sm font-semibold" style={{ color: 'var(--text-ink)' }}>{d.tool}</span>
          <span className="text-xs font-mono truncate max-w-[130px] opacity-50" style={{ color: 'var(--text-muted)' }}>
            {d.action_id.slice(0, 18)}...
          </span>
        </div>
        <div className="text-xs mt-0.5 line-clamp-1" style={{ color: 'var(--text-muted)' }}>{d.reason}</div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {d.domains?.map((dom) => (
            <span
              key={dom}
              className="text-[11px] font-mono px-2 py-0.5 rounded border"
              style={{
                borderColor: 'var(--border-line)',
                background: 'rgba(150, 140, 170, 0.08)',
                color: 'var(--text-muted)',
              }}
            >
              {dom}
            </span>
          ))}
        </div>
      </div>
      <div className="flex-shrink-0">
        <VerdictChip verdict={d.classification} />
      </div>
    </div>
  )
}

// ── Receipt Row ───────────────────────────────────────────────────────────

function ReceiptRow({ r }: { r: ReceiptSummary }) {
  return (
    <Link href={`/proof?receipt=${r.id}`} className="block group">
      <div
        className="flex items-center gap-4 py-3 px-3 rounded-lg border transition-all hover:border-[var(--rubicon-threshold)]"
        style={{
          borderColor: 'var(--border-line)',
          background: 'rgba(150, 140, 170, 0.04)',
        }}
      >
        <VerdictChip verdict={r.decision} />
        <div className="flex-1 font-mono text-xs truncate group-hover:text-red-500 transition-colors" style={{ color: 'var(--text-ink)' }}>
          {r.id.slice(0, 22)}...
        </div>
        <div className="text-xs font-mono opacity-60" style={{ color: 'var(--text-muted)' }}>
          {r.domain_results?.length} domains
        </div>
        {r.signature_present && (
          <span className="text-xs font-mono font-semibold text-emerald-500 flex items-center gap-1">
            ✓ signed
          </span>
        )}
      </div>
    </Link>
  )
}

// ── Dashboard Page ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [telemetry, setTelemetry] = useState<TelemetryStatus | null>(null)
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Immediate pre-seed from bundled results.json to ensure 21 receipts always display instantly
    fetch('/results.json')
      .then((r) => r.json())
      .then((camp) => {
        if (camp?.drills) {
          const list = camp.drills.map((dr: { drill_id: string; action_digest: string; verifier_verdict: string; domains: string[]; receipt_signature?: string }) => ({
            id: `${dr.drill_id}_receipt`,
            session_id: `rubicon-campaign-${dr.drill_id.toLowerCase()}`,
            action_id: dr.action_digest,
            decision: dr.verifier_verdict,
            domain_results: (dr.domains || []).map((dm: string) => ({ domain: dm, result: dr.verifier_verdict })),
            signature_present: Boolean(dr.receipt_signature),
          }))
          setReceipts(list)
        }
      })
      .catch(() => {})

    const load = async () => {
      try {
        const [s, d, r, t] = await Promise.allSettled([
          api.status(),
          api.decisions(20),
          api.receipts(),
          api.telemetryStatus(),
        ])
        if (s.status === 'fulfilled') setStatus(s.value)
        if (d.status === 'fulfilled') setDecisions(d.value.decisions || [])
        if (r.status === 'fulfilled' && r.value.receipts?.length) {
          setReceipts(r.value.receipts)
        }
        if (t.status === 'fulfilled') setTelemetry(t.value)
      } catch {
        // keep pre-seeded receipts intact
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen overflow-x-hidden w-full max-w-full pb-20">
      {/* Site Navigation */}
      <nav
        className="border-b px-4 sm:px-6 h-16 flex items-center justify-between backdrop-blur-md sticky top-0 z-50 transition-colors"
        style={{
          background: 'var(--nav-bg)',
          borderColor: 'var(--nav-border)',
        }}
      >
        <div className="flex items-center gap-3 sm:gap-6 min-w-0">
          <Link href="/" className="font-mono font-bold tracking-widest text-base sm:text-lg shrink-0" style={{ color: 'var(--text-ink)' }}>
            RUBICON
          </Link>
          <div className="flex items-center gap-3 sm:gap-5 pl-2 sm:pl-3">
            <span className="text-xs font-mono px-2 py-0.5 rounded border border-current opacity-70">
              dashboard
            </span>
            <Link href="/proof" className="text-xs sm:text-sm font-medium transition-colors hover:text-red-500" style={{ color: 'var(--text-muted)' }}>
              Proof
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <ThemeToggle />
          <Link
            href="/demo"
            className="hidden sm:inline-block px-3 py-1.5 rounded-lg text-xs font-mono font-semibold text-white shadow-md transition-all hover:scale-[1.02]"
            style={{
              background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
            }}
          >
            RUN R07 DEMO ➔
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        {/* Workspace Heading */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="workspace-kicker mb-3">
              <span className="live-dot" />
              <span>PreToolUse Gateway · 12 State Domains Active</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-ink)' }}>
              Reversibility &amp; Boundary Desk
            </h1>
            <p className="text-sm md:text-base max-w-2xl" style={{ color: 'var(--text-muted)' }}>
              Real-time action interception, fail-closed permit gating, and independent post-rollback state reconciliation.
            </p>
          </div>
          <Link
            href="/demo"
            className="px-5 py-3 rounded-xl font-mono text-xs font-bold text-white transition-all hover:scale-[1.02] shadow-lg shrink-0 self-start md:self-auto flex items-center gap-2"
            style={{
              background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
              boxShadow: '0 4px 15px rgba(220, 20, 60, 0.35)',
            }}
          >
            RUN R07 DEMO ➔
          </Link>
        </div>

        {/* ── PANEL 1: RECORDED PROOF (Permanent Corpus) ────────────────────────── */}
        <div className="mb-10">
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm" />
              <span className="text-xs font-mono uppercase tracking-widest font-bold text-emerald-500">
                RECORDED PROOF · PERMANENT BENCHMARK CORPUS
              </span>
            </div>
            <span className="text-xs font-mono text-emerald-500 font-semibold">
              21 Drills · 21 Signed Receipts · 12 Domains · 100% Verified
            </span>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mb-3"
          >
            <MetricCard value="21" label="Drills Evaluated" sub="Across 12 Domains" />
            <MetricCard value="3" label="Ablation Arms" sub="Raw vs Gate vs Verified" />
            <MetricCard value="12" label="State Domains" sub="Complete Classification" />
            <MetricCard value="21/21" label="Signed Receipts" sub="100% Ed25519 Verified" />
            <MetricCard value="14" label="Escapes Blocked" sub="14/14 Caught (100%)" accent />
            <MetricCard value="0" label="Escapes Allowed" sub="0 Escapes under Rubicon" accent />
          </motion.div>
          <div className="text-[11px] font-mono opacity-60" style={{ color: 'var(--text-muted)' }}>
            ✓ Permanent proof corpus is stored on disk and verifiable without running Bob.
          </div>
        </div>

        {/* ── PANEL 2: LIVE SESSION TELEMETRY ───────────────────────────────────── */}
        <div className="rubicon-card p-5 mb-10 border" style={{ borderColor: 'var(--border-line)' }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b" style={{ borderColor: 'var(--border-line)' }}>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase tracking-widest font-bold" style={{ color: 'var(--text-ink)' }}>
                LIVE BOB SESSION
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold uppercase tracking-wider border flex items-center gap-1.5 ${
                  telemetry?.status === 'LIVE'
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${telemetry?.status === 'LIVE' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                {telemetry?.status === 'LIVE' ? 'BOB SESSION LIVE' : 'BOB SESSION DISCONNECTED'}
              </span>
            </div>
            <div className="text-xs font-mono opacity-70" style={{ color: 'var(--text-muted)' }}>
              Observer Telemetry Only · Render Does Not Run Bob
            </div>
          </div>

          {telemetry?.status === 'LIVE' ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
              <div className="p-3 rounded-lg border bg-white/[0.02]" style={{ borderColor: 'var(--border-line)' }}>
                <div className="opacity-60 text-[10px] uppercase mb-1">Live Events</div>
                <div className="text-lg font-bold text-emerald-400">{telemetry.total_events}</div>
              </div>
              <div className="p-3 rounded-lg border bg-white/[0.02]" style={{ borderColor: 'var(--border-line)' }}>
                <div className="opacity-60 text-[10px] uppercase mb-1">Actions Blocked</div>
                <div className="text-lg font-bold text-rose-400">{telemetry.blocked_count}</div>
              </div>
              <div className="p-3 rounded-lg border bg-white/[0.02]" style={{ borderColor: 'var(--border-line)' }}>
                <div className="opacity-60 text-[10px] uppercase mb-1">Actions Allowed</div>
                <div className="text-lg font-bold text-emerald-400">{telemetry.allowed_count}</div>
              </div>
              <div className="p-3 rounded-lg border bg-white/[0.02]" style={{ borderColor: 'var(--border-line)' }}>
                <div className="opacity-60 text-[10px] uppercase mb-1">Active Session</div>
                <div className="truncate text-xs" title={telemetry.session_id || ''}>{telemetry.session_id || 'unknown'}</div>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl border bg-black/10 dark:bg-black/30 text-xs font-mono" style={{ borderColor: 'var(--border-line)' }}>
              <div className="font-semibold text-amber-400 mb-1">
                0 live events · Bob not currently streaming
              </div>
              <p className="opacity-75 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                To connect a live session, run IBM Bob on builder machine with the PreToolUse hook configured:
                <code className="mx-1 px-1.5 py-0.5 rounded bg-white/10 text-red-400">python scripts/hooks/pretooluse.py</code>.
                When actions are proposed, redacted metadata will appear here in real time.
              </p>
            </div>
          )}
        </div>

        {/* The Rubicon Line Visualizer */}
        <div className="rubicon-card p-6 mb-10">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>
              The Rubicon Line: Effect Boundary Envelope
            </div>
            <div className="text-xs font-mono text-emerald-500 font-medium">
              Fail-closed policy active
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono mb-3">
            <div className="text-emerald-500 font-semibold">SAFE (ROLLBACK-COVERED)</div>
            <div style={{ color: 'var(--rubicon-threshold)' }} className="font-bold">
              THE RUBICON LINE
            </div>
            <div className="text-rose-500 font-semibold">EXTERNAL (UNCOVERED)</div>
          </div>
          <div className="rubicon-river-line w-full" />
        </div>

        {/* Main Grid: Stream & Receipts */}
        <div className="grid lg:grid-cols-2 gap-8 mb-10">
          {/* Decisions Ledger */}
          <div className="rubicon-card p-6 min-w-0">
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>
                Recent agent decisions
              </div>
              <span className="text-xs font-mono opacity-60" style={{ color: 'var(--text-muted)' }}>
                {decisions.length} recorded
              </span>
            </div>
            {decisions.length === 0 ? (
              <div className="text-xs font-mono py-12 text-center opacity-70 flex flex-col items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                <span>No live agent decisions streaming currently.</span>
                <span className="text-[11px] opacity-80">Start IBM Bob locally with PreToolUse hook or inspect recorded drills:</span>
                <Link
                  href="/demo"
                  className="mt-1 px-3 py-1 rounded border text-red-400 border-red-500/30 hover:bg-red-500/10 transition-all font-semibold"
                >
                  RUN R07 DEMO REPLAY ➔
                </Link>
              </div>
            ) : (
              <div className="overflow-y-auto max-h-[380px] space-y-1 pr-1">
                {decisions.map((d, i) => (
                  <DecisionRow key={`${d.action_id}-${i}`} d={d} />
                ))}
              </div>
            )}
          </div>

          {/* Reversibility Receipts */}
          <div className="rubicon-card p-6 min-w-0">
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>
                Cryptographic receipts
              </div>
              <span className="text-xs font-mono opacity-60" style={{ color: 'var(--text-muted)' }}>
                {receipts.length} verified
              </span>
            </div>
            {receipts.length === 0 ? (
              <div className="text-xs font-mono py-12 text-center opacity-50" style={{ color: 'var(--text-muted)' }}>
                No receipts yet. Run the benchmark to generate verified receipts.
              </div>
            ) : (
              <div className="overflow-y-auto max-h-[380px] space-y-2.5 pr-1">
                {receipts.map((r) => (
                  <ReceiptRow key={r.id} r={r} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Domain Coverage Matrix */}
        <div className="rubicon-card p-6 overflow-hidden min-w-0">
          <div className="flex items-center justify-between mb-6">
            <div className="text-xs font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>
              Domain coverage &amp; rollback contract matrix
            </div>
            <span className="text-xs font-mono text-emerald-500 font-semibold">12 Domains Defined</span>
          </div>
          <div className="overflow-x-auto w-full">
            <table className="w-full text-sm min-w-[540px]">
              <thead>
                <tr className="border-b text-left text-xs font-mono opacity-60" style={{ borderColor: 'var(--border-line)', color: 'var(--text-muted)' }}>
                  <th className="py-2.5 px-3 font-semibold">Domain</th>
                  <th className="py-2.5 px-3 font-semibold">Rollback Coverage</th>
                  <th className="py-2.5 px-3 font-semibold">Enforcement Policy</th>
                  <th className="py-2.5 px-3 font-semibold">Verifier Adapter</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-line)' }}>
                {[
                  { domain: 'WORKSPACE_TRACKED', coverage: 'INSIDE', policy: 'COVERED_REVERSIBLE', adapter: 'filesystem' },
                  { domain: 'WORKSPACE_IGNORED', coverage: 'EXCLUDED', policy: 'BOUNDARY_REQUIRES_PERMIT', adapter: 'filesystem' },
                  { domain: 'WORKSPACE_EXCLUDED', coverage: 'EXCLUDED', policy: 'OUTSIDE_ROLLBACK', adapter: 'filesystem' },
                  { domain: 'VCS_LOCAL', coverage: 'UNKNOWN', policy: 'BOUNDARY_REQUIRES_PERMIT', adapter: 'git' },
                  { domain: 'VCS_REMOTE', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'git' },
                  { domain: 'DATABASE_STATE', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'sqlite' },
                  { domain: 'EXTERNAL_NETWORK', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'http_fixture' },
                  { domain: 'PROCESS_RUNTIME', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'process' },
                  { domain: 'OUTSIDE_WORKSPACE', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'filesystem' },
                  { domain: 'CREDENTIAL_STATE', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'filesystem' },
                  { domain: 'PACKAGE_REGISTRY', coverage: 'OUTSIDE', policy: 'OUTSIDE_ROLLBACK', adapter: 'registry' },
                  { domain: 'UNKNOWN', coverage: 'UNKNOWN', policy: 'UNKNOWN_EFFECT', adapter: 'none (fail-closed)' },
                ].map((row) => (
                  <tr key={row.domain} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-3 font-mono text-xs font-semibold" style={{ color: 'var(--text-ink)' }}>
                      {row.domain}
                    </td>
                    <td className="py-3 px-3">
                      <VerdictChip verdict={row.coverage === 'INSIDE' ? 'RESTORED' : row.coverage === 'UNKNOWN' ? 'UNKNOWN' : 'BREACH'} />
                    </td>
                    <td className="py-3 px-3">
                      <VerdictChip verdict={row.policy} />
                    </td>
                    <td className="py-3 px-3 font-mono text-xs opacity-70" style={{ color: 'var(--text-muted)' }}>
                      {row.adapter}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
