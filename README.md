# thananan-p-skills

Agent skills for horoacademy and day-to-day frontend work, installable via [`npx skills`](https://github.com/vercel-labs/skills).

## Install

```bash
npx skills add thannnp/thananan-p-skills
```

This scans the repo for all skills and shows an interactive menu to pick which ones to install.

List available skills without installing:

```bash
npx skills add thannnp/thananan-p-skills --list
```

Install a specific skill only:

```bash
npx skills add thannnp/thananan-p-skills --skill horo-db
```

## Available skills

| Skill | Purpose |
|---|---|
| `horo-db` | Assistant for answering questions about the structure and relationships of the two horoacademy databases (`horoacademy-backoffice` and `horoacademy-wpe-service`) — which tables exist, what columns they have, how they relate, cross-DB references, and polymorphic relations. |
| `horo-summon-money` | Local-only testing helper that forces the payment status of a payment link or payment transaction (`successful` / `pending` / `failed` / `expired` / `reversed`). Accepts either a payment-link id or a transaction id; supports a direct (tinker) mode and a real Omise webhook mode. Only touches payment state — does not notify wpe-service. |
| `horo-bazi` | Reference assistant for the Chinese astrology (Bazi / ปาจื้อ / ดวงจีน) rule set used by horoacademy — stems/branches tables, chart construction, day-master strength scoring, favorable elements, stem/branch interactions (ฮะ ชง คัก เฮ้ง ไห่ ผั่ว ซาฮะ ซาหุย หลักฮะ), ten gods, auspicious stars, luck cycles (วัยจร), and flying stars (ซำง้วน). Transcribed from the "วิชาดวงจีน 1" course document; intended both for answering questions and for implementing calculation features (e.g. CoupleMatching). |
| `tailwind-snap` | Snaps px values from a design onto the nearest Tailwind token instead of arbitrary values (`text-[13px]` → `text-xs`, `p-[15px]` → `p-4`). Covers every scale — spacing, font size, line height, radius, border, shadow, tracking, opacity — reads the project's `@theme` first so project tokens win over framework defaults, and reports the resulting drift. Ships an audit script for sweeping existing markup. Token values verified against `tailwindcss@4.3.1`; v3 differences documented. |
| `weekly` | Weekly work recap. Pulls the week's real activity from four sources — pull requests you opened, PRs you reviewed, issues you touched, commits in local clones, and the prompts you typed in Claude Code (which catch the work that leaves no git trace: prod firefighting, DB permissions, chasing other people's tickets) — then marks every item with where it actually landed: shipped to production, merged to `dev` but not yet released, or still on a branch. Detects the repos whose `main`/`dev` histories have permanently diverged, and flags PRs that show as merged but whose sha is nowhere in `main` (swallowed by a squash). Writes the summary as a fixed-shape Markdown note so a downstream agent can read it back. |

## Repo structure

```
thananan-p-skills/
└── skills/
    ├── horo-db/
    │   ├── SKILL.md                              # instructions (English; replies to the user in Thai)
    │   ├── HORO_BACKOFFICE_DATABASE_DIAGRAM.md   # Mermaid ER diagram — backoffice
    │   └── WPE_SERVICE_DATABASE_DIAGRAM.md       # Mermaid ER diagram — wpe-service
    ├── horo-summon-money/
    │   └── SKILL.md                              # instructions (English; asks the user in Thai)
    ├── horo-bazi/
    │   ├── SKILL.md                              # instructions (English; replies to the user in Thai)
    │   └── references/
    │       ├── 01-pillars.md                     # elements, stems, branches, month/hour pillar tables
    │       ├── 02-day-master.md                  # strength scoring, favorable elements, HL rules
    │       ├── 03-interactions.md                # ฮะ คัก ชง เฮ้ง ไห่ ผั่ว ซาฮะ ซาหุย หลักฮะ, hidden elements
    │       ├── 04-ten-gods-stars.md              # ten gods, auspicious stars, directions
    │       ├── 05-luck-cycles.md                 # luck pillars (วัยจร)
    │       └── 06-flying-stars.md                # ซำง้วน 9 stars, month/hour stars, 64 gua
    ├── tailwind-snap/
    │   ├── SKILL.md                              # snapping rules + drift report
    │   ├── reference/
    │   │   └── tokens.md                         # full v4 default scale, verified; v3 differences
    │   └── scripts/
    │       └── snap.py                           # px -> token lookup, and --audit for existing files
    └── weekly/
        ├── SKILL.md                              # note shape + writing rules (Thai output)
        └── scripts/
            ├── collect.py                        # gathers PRs, issues, commits, typed prompts -> JSON
            ├── outline.py                        # compact views of that JSON, so the full file is never read
            └── publish.sh                        # pushes the finished note to a private worklog repo
```

To add a new skill, create `skills/<name>/SKILL.md` and `npx skills` will discover it automatically.
