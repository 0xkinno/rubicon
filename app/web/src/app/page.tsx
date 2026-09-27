'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ThemeToggle } from '@/components/ThemeToggle'

// ── Rubicon River Line ─────────────────────────────────────────────────────

function RubiconThresholdVisual() {
  return (
    <div className="relative flex items-center justify-center w-full my-12 overflow-hidden px-4">
      <div className="hidden sm:flex absolute inset-y-0 left-0 w-1/2 items-center">
        <div className="w-full h-px opacity-30 bg-gradient-to-r from-transparent to-red-500" />
        <span className="ml-3 text-xs font-mono tracking-widest uppercase opacity-70 whitespace-nowrap text-emerald-400">
          Rollback covers
        </span>
      </div>
      <div className="relative z-10 flex flex-col items-center">
        <div className="w-px h-8 bg-gradient-to-b from-transparent to-[#DC143C]" />
        <div
          className="px-4 py-1.5 rounded-full text-xs font-mono font-bold tracking-widest border shadow-lg"
          style={{
            background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 50%, #D97706 100%)',
            color: '#ffffff',
            borderColor: '#DC143C',
            boxShadow: '0 0 20px rgba(220, 20, 60, 0.4)',
          }}
        >
          THE RUBICON LINE
        </div>
        <div className="w-px h-8 bg-gradient-to-t from-transparent to-[#DC143C]" />
      </div>
      <div className="hidden sm:flex absolute inset-y-0 right-0 w-1/2 items-center justify-end">
        <span className="mr-3 text-xs font-mono tracking-widest uppercase opacity-70 whitespace-nowrap text-rose-400">
          Outside rollback
        </span>
        <div className="w-full h-px opacity-30 bg-gradient-to-l from-transparent to-red-500" />
      </div>
    </div>
  )
}

// ── Domain Chip ────────────────────────────────────────────────────────────

function DomainChip({
  label,
  covered,
}: {
  label: string
  covered: boolean
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-semibold transition-all ${
        covered
          ? 'chip-restored'
          : 'chip-breach'
      }`}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{
          background: covered ? '#34d399' : '#ff4d6d',
          boxShadow: covered ? '0 0 6px #34d399' : '0 0 6px #ff4d6d',
        }}
      />
      {label}
    </span>
  )
}

// ── Stat card with OpenStock Luster ────────────────────────────────────────

function StatCard({
  value,
  label,
  accent = false,
}: {
  value: string
  label: string
  accent?: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="rubicon-card p-6"
    >
      <div
        className="text-4xl font-bold tabular-nums mb-2 font-mono"
        style={{
          color: accent ? 'var(--rubicon-threshold)' : 'var(--text-ink)',
          textShadow: accent ? '0 0 20px rgba(220, 20, 60, 0.3)' : 'none',
        }}
      >
        {value}
      </div>
      <div className="text-sm font-medium opacity-80" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
    </motion.div>
  )
}

// ── Flow Step ──────────────────────────────────────────────────────────────

function Step({
  num,
  title,
  body,
}: {
  num: string
  title: string
  body: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      className="rubicon-card p-6 flex gap-5 items-start"
    >
      <div
        className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-mono font-bold text-white shadow-md"
        style={{ background: 'linear-gradient(135deg, #8B0000, #DC143C)' }}
      >
        {num}
      </div>
      <div>
        <div className="font-semibold mb-1 text-base tracking-tight" style={{ color: 'var(--text-ink)' }}>
          {title}
        </div>
        <div className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          {body}
        </div>
      </div>
    </motion.div>
  )
}

// ── Landing Page ───────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-x-hidden w-full max-w-full">
      {/* Site Navigation */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b transition-colors"
        style={{
          background: 'var(--nav-bg)',
          borderColor: 'var(--nav-border)',
        }}
      >
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse shadow-red-500/50 shadow-md" />
              <span className="font-mono font-bold tracking-widest text-lg" style={{ color: 'var(--text-ink)' }}>
                RUBICON
              </span>
            </Link>
            <span className="hidden md:inline text-xs font-mono opacity-50 px-2 py-0.5 rounded border border-current">
              v1.0.0
            </span>
          </div>

          <div className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm font-medium transition-colors hover:text-red-500"
              style={{ color: 'var(--text-muted)' }}
            >
              Dashboard
            </Link>
            <Link
              href="/proof"
              className="text-sm font-medium transition-colors hover:text-red-500"
              style={{ color: 'var(--text-muted)' }}
            >
              Proof
            </Link>
            <ThemeToggle />
            <Link
              href="/proof"
              className="px-4 py-1.5 rounded-lg text-xs font-mono font-semibold text-white transition-transform hover:scale-[1.02] shadow-md"
              style={{
                background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
                boxShadow: '0 4px 15px rgba(220, 20, 60, 0.3)',
              }}
            >
              For judges ↗
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section with Cinematic Background Backdrop */}
      <section className="relative min-h-[92vh] flex items-center pt-28 pb-20 px-6 overflow-hidden">
        {/* Cinematic Backdrop Image Layer */}
        <div className="absolute inset-0 z-0 pointer-events-none select-none">
          <img
            src="/rubicon_hero_bg.jpg"
            alt="Rubicon Threshold Landscape"
            className="w-full h-full object-cover object-right md:object-center opacity-70 dark:opacity-85 filter contrast-105"
          />
          {/* Subtle Dark Vignette & Gradient Overlays for High Contrast Typography */}
          <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/60 to-transparent dark:from-black/95 dark:via-black/75 dark:to-black/30" />
          <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg-paper)] via-transparent to-transparent" />
        </div>

        <div className="max-w-5xl mx-auto w-full relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="workspace-kicker mb-8 shadow-sm">
              <span className="live-dot" aria-hidden="true" />
              <span>IBM Bob 2.0 Hackathon · Effect Boundary Enforcer</span>
            </div>

            <h1
              className="font-bold leading-[1.04] tracking-tight mb-8 text-white"
              style={{
                fontSize: 'clamp(2.75rem, 6.5vw, 5rem)',
                fontFamily: '"Helvetica Neue", Helvetica, -apple-system, sans-serif',
                textShadow: '0 4px 20px rgba(0, 0, 0, 0.6)',
              }}
            >
              Bob can undo your files.
              <br />
              <span
                style={{
                  background: 'linear-gradient(135deg, #FF2A55 0%, #FFAA00 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Can it undo
              </span>{' '}
              what those
              <br />
              files already caused?
            </h1>

            <p className="text-xl md:text-2xl text-gray-200 max-w-2xl leading-relaxed mb-10 font-normal drop-shadow">
              Rubicon tells you exactly where Bob&apos;s rollback stops, and proves what
              remained after rollback. Classify every action. Enforce a human permit at
              the boundary. Independently verify every state domain.
            </p>

            <div className="flex flex-wrap gap-4 items-center mb-16">
              <Link
                href="/proof"
                className="px-8 py-3.5 rounded-xl font-semibold text-white transition-all hover:scale-[1.02] shadow-xl text-base"
                style={{
                  background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
                  boxShadow: '0 8px 25px rgba(220, 20, 60, 0.4)',
                }}
              >
                Run the proof ↗
              </Link>
              <Link
                href="/dashboard"
                className="px-8 py-3.5 rounded-xl font-semibold border transition-all hover:bg-white/10 text-white backdrop-blur-md text-base"
                style={{ borderColor: 'rgba(255, 255, 255, 0.25)' }}
              >
                Open dashboard
              </Link>
            </div>

            {/* Live Status Pill Strip */}
            <div className="inline-flex flex-wrap items-center gap-3 p-2 rounded-xl bg-black/50 backdrop-blur-md border border-white/10 text-xs font-mono text-gray-300">
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
                21/21 Drills Verified
              </span>
              <span className="text-white/40">·</span>
              <span>100% Classifier Accuracy</span>
              <span className="text-white/40">·</span>
              <span className="text-rose-400 font-semibold">0 Boundary Escapes</span>
              <span className="text-white/40">·</span>
              <span>Ed25519 Signed Receipts</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* The Rollback Assumption Section */}
      <section className="py-24 px-6 border-y" style={{ borderColor: 'var(--border-line)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="workspace-kicker mb-4">
            <span className="live-dot" />
            <span>Problem Discovery</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            The rollback assumption
          </h2>
          <p className="text-lg leading-relaxed mb-10 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            When an IBM Bob agent runs in auto-approve mode, it can execute dozens of tool
            calls without manual review. Bob&apos;s rollback recovers workspace files, but only
            a bounded subset of what the agent actually changed.
          </p>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="rubicon-card p-8">
              <div className="flex items-center gap-2.5 font-semibold text-emerald-500 text-lg mb-4">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                </svg>
                What Bob rollback covers
              </div>
              <ul className="space-y-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                <li className="flex items-center gap-2">• Tracked workspace files (snapshotted at task start)</li>
                <li className="flex items-center gap-2">• File writes within the workspace boundary</li>
                <li className="flex items-center gap-2">• Standard source code modifications</li>
                <li className="flex items-center gap-2">• Line-level diffs within repository root</li>
              </ul>
            </div>

            <div className="rubicon-card p-8">
              <div className="flex items-center gap-2.5 font-semibold text-rose-500 text-lg mb-4">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
                What Bob rollback does NOT cover
              </div>
              <ul className="space-y-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                <li className="flex items-center gap-2">• Remote Git refs (already pushed to origin)</li>
                <li className="flex items-center gap-2">• .gitignore-excluded files and .env credentials</li>
                <li className="flex items-center gap-2">• Database mutations (SQLite rows persist)</li>
                <li className="flex items-center gap-2">• Detached background daemon processes</li>
                <li className="flex items-center gap-2">• External HTTP/API network mutations</li>
                <li className="flex items-center gap-2">• Files written outside the workspace root</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Threshold Visual & Domain Registry */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="workspace-kicker mb-4">
            <span className="live-dot" />
            <span>State Boundary</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-3 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            The effect boundary
          </h2>
          <p className="mb-10 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Every Bob agent action is mapped to one or more state domains. Rubicon determines
            which side of the line each domain lives on before execution.
          </p>

          <div className="flex flex-wrap gap-2.5 justify-center mb-6">
            {[
              { label: 'WORKSPACE_TRACKED', covered: true },
              { label: 'VCS_LOCAL', covered: false },
              { label: 'VCS_REMOTE', covered: false },
              { label: 'DATABASE_STATE', covered: false },
              { label: 'EXTERNAL_NETWORK', covered: false },
              { label: 'PROCESS_RUNTIME', covered: false },
              { label: 'OUTSIDE_WORKSPACE', covered: false },
              { label: 'CREDENTIAL_STATE', covered: false },
              { label: 'PACKAGE_REGISTRY', covered: false },
            ].map((d) => (
              <DomainChip key={d.label} label={d.label} covered={d.covered} />
            ))}
          </div>

          <RubiconThresholdVisual />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-10">
            <div className="rubicon-card p-6 text-center">
              <div className="text-sm font-mono font-bold text-emerald-500 mb-2">COVERED_REVERSIBLE</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Auto-approved. Bob rollback restores this domain completely.
              </div>
            </div>
            <div className="rubicon-card p-6 text-center">
              <div className="text-sm font-mono font-bold text-amber-500 mb-2">BOUNDARY_REQUIRES_PERMIT</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Fenced. Requires an explicit, single-use Ed25519 human permit.
              </div>
            </div>
            <div className="rubicon-card p-6 text-center">
              <div className="text-sm font-mono font-bold text-rose-500 mb-2">OUTSIDE_ROLLBACK</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Blocked fail-closed. Bob rollback cannot restore this domain.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Verified Campaign Results */}
      <section className="py-24 px-6 border-y" style={{ borderColor: 'var(--border-line)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="workspace-kicker mb-4">
            <span className="live-dot" />
            <span>Empirical Evidence</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-10 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            Causal benchmark results
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <StatCard value="21" label="Total drills run (R01 to R21)" />
            <StatCard value="3" label="Ablation arms (A / B / C)" />
            <StatCard value="100%" label="Outside-rollback classified" accent />
            <StatCard value="0" label="Boundary escapes allowed" accent />
          </div>
          <p className="mt-8 text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            * Verified metrics from the 21-drill causal benchmark (Arm A baseline vs. Arm B &amp; C enforced).
            All SHA-256 state manifests and Ed25519 receipts cryptographically verified.
          </p>
        </div>
      </section>

      {/* How Rubicon Works */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="workspace-kicker mb-4">
            <span className="live-dot" />
            <span>Architecture</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-12 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            How Rubicon works
          </h2>
          <div className="space-y-6">
            <Step
              num="1"
              title="PreToolUse hook intercepts every Bob tool call"
              body="Before Bob executes any tool, Rubicon's deterministic classifier inspects the tool name, inputs, file paths, commands, and network targets."
            />
            <Step
              num="2"
              title="Effect vector maps action to state domains"
              body="Each action is classified across 12 state domains. Actions touching domains outside Bob's rollback contract are blocked fail-closed until an Ed25519 permit is issued."
            />
            <Step
              num="3"
              title="Post-rollback verifier issues Reversibility Receipt"
              body="After Bob completes rollback, Rubicon's independent verifier hashes all 12 domains from scratch and issues a tamper-evident, cryptographically signed receipt."
            />
          </div>
        </div>
      </section>

      {/* IBM Bob Integration */}
      <section className="py-24 px-6 border-y" style={{ borderColor: 'var(--border-line)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="workspace-kicker mb-4">
            <span className="live-dot" />
            <span>Core Integration</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            IBM Bob integration
          </h2>
          <p className="mb-10 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Rubicon integrates directly into IBM Bob IDE as an essential safety gate, not a superficial claim.
          </p>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="rubicon-card p-6">
              <div className="font-mono text-sm font-bold text-red-500 mb-2">PreToolUse hook</div>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Blocks dangerous actions before execution via exit code 2. Configured in <code>.bob/settings.json</code>.
              </p>
            </div>
            <div className="rubicon-card p-6">
              <div className="font-mono text-sm font-bold text-amber-500 mb-2">PostToolUse hook</div>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Records post-execution state for manifest comparison. Observational only, does not alter execution.
              </p>
            </div>
            <div className="rubicon-card p-6">
              <div className="font-mono text-sm font-bold text-emerald-500 mb-2">Bob Rollback</div>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Invoked by the human in Bob IDE. Rubicon independently inspects all domains to prove whether restoration succeeded.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Judge / Evidence CTA */}
      <section className="py-24 px-6 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight" style={{ color: 'var(--text-ink)' }}>
            For judges &amp; reviewers
          </h2>
          <p className="text-base mb-8" style={{ color: 'var(--text-muted)' }}>
            The proof page answers all 10 required judge questions with verifiable evidence, including
            receipt hashes, domain-level verdicts, and Ed25519 signature checks.
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/proof"
              className="px-8 py-3.5 rounded-xl font-semibold text-white shadow-lg text-sm transition-transform hover:scale-[1.02]"
              style={{
                background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
              }}
            >
              View proof evidence ↗
            </Link>
            <Link
              href="/dashboard"
              className="px-8 py-3.5 rounded-xl font-semibold border text-sm transition-colors hover:bg-black/5 dark:hover:bg-white/5"
              style={{ borderColor: 'var(--border-line)', color: 'var(--text-ink)' }}
            >
              Open dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 px-6 text-xs font-mono" style={{ borderColor: 'var(--border-line)', color: 'var(--text-muted)' }}>
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div>RUBICON · IBM Bob 2.0 Hackathon | Effect Boundary Governance</div>
          <div className="flex gap-6">
            <Link href="/dashboard" className="hover:underline">Dashboard</Link>
            <Link href="/proof" className="hover:underline">Proof</Link>
            <a href="https://github.com/0xkinno/rubicon" target="_blank" rel="noopener noreferrer" className="hover:underline">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
