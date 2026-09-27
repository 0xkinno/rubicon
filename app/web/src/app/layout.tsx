import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'RUBICON: Bob Rollback Effect Boundary Enforcer',
  description:
    'Rubicon tells developers what IBM Bob can actually undo, and stops dangerous actions before they cross that line.',
  keywords: ['IBM Bob', 'rollback', 'AI safety', 'developer tooling', 'effect boundary'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
