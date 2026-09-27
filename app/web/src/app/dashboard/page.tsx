'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { api, type StatusResponse, type Decision, type ReceiptSummary } from '@/lib/api'
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
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, d, r] = await Promise.all([
          api.status(),
          api.decisions(20),
          api.receipts(),
        ])
        setStatus(s)
        setDecisions(d.decisions)
        setReceipts(r.receipts)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'API server offline: start with uvicorn app.api.main:app')
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen overflow-x-hidden w-full max-w-full pb-20">
      {/* Site Navigation */}
      <nav
        className="border-b px-6 h-16 flex items-center justify-between backdrop-blur-md sticky top-0 z-50 transition-colors"
        style={{
          background: 'var(--nav-bg)',
          borderColor: 'var(--nav-border)',
        }}
      >
        <div className="flex items-center gap-4">
          <Link href="/" className="font-mono font-bold tracking-widest text-lg" style={{ color: 'var(--text-ink)' }}>
            RUBICON
          </Link>
          <span className="opacity-30">/</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded border border-current opacity-70">
            dashboard
          </span>
        </div>
        <div className="flex items-center gap-5">
          <Link href="/proof" className="text-sm font-medium transition-colors hover:text-red-500" style={{ color: 'var(--text-muted)' }}>
            Proof
          </Link>
          <ThemeToggle />
          <div
            className={`w-2.5 h-2.5 rounded-full ${status ? 'bg-emerald-500 shadow-emerald-500/50 shadow-md' : 'bg-rose-500'}`}
            title={status ? 'Live API Connected' : 'Connecting to API'}
          />
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* Workspace Heading (OpenStock Pattern) */}
        <div className="mb-10">
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

        {error && (
          <div className="mb-8 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 font-mono text-xs">
            {error}
          </div>
        )}

        {/* Metrics Row */}
        {status && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10"
          >
            <MetricCard value={status.decisions_total} label="Total decisions" />
            <MetricCard value={status.allowed} label="Allowed safe" />
            <MetricCard value={status.blocked} label="Blocked breaches" accent />
            <MetricCard value={status.receipts_total} label="Receipts issued" />
            <MetricCard
              value={status.public_key_loaded ? '✓ Loaded' : '✗ Missing'}
              label="Signing key"
              sub="Ed25519 external"
              accent={!status.public_key_loaded}
            />
          </motion.div>
        )}

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
              <div className="text-xs font-mono py-12 text-center opacity-50" style={{ color: 'var(--text-muted)' }}>
                No decisions yet. Start Bob with the PreToolUse hook configured.
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
