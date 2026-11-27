# Design System — Papita Web

## Surface & Palette (OKLCH)

- **Canvas:** `--background: oklch(0.975 0.008 220)` (light) / `oklch(0.155 0.02 235)` (dark)
- **Card / Surface:** `--card: oklch(1 0 0)` / `oklch(0.205 0.022 235)`
- **Primary Accent:** `--primary: oklch(0.45 0.13 212)` (teal-cyan) / `oklch(0.72 0.12 205)` (dark)
- **Sidebar:** `#04090c` obsidian rail (`--sidebar-foreground: oklch(0.93 0.012 220)`)
- **Semantic Status:** `--success` (`156`), `--warning` (`70`), `--info` (`225`), `--destructive` (`25`)

## Layout & Components

- **Shell:** Persistent obsidian left sidebar (`AppLayout`) + sticky top header bar with global search (`/` / `⌘K`), locale switcher, and AI assistant drawer
- **Radius & Borders:** `--radius: 0.5rem`, crisp `1px` `--border` hairlines
- **Controls:** Tailwind CSS v4 + shadcn-style primitives (`Button`, `ActionIconButton`, `Dialog`, `Tabs`)
- **Numbers & Data:** Tabular numerals for currency/amounts, high-contrast status pills, interactive SVG charts
