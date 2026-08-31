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
| `clio-brownbook` | Weekly work log — the writing half of a two-part setup (the reading half, `clio-echo`, lives on a personal-secretary box and only reads the finished note). Pulls the week's real activity from PRs opened, PRs reviewed, issues touched, local commits, and the prompts typed in Claude Code — that last source catches the work that leaves no git trace: prod firefighting, database permissions, chasing someone else's ticket. Marks every item with where it actually landed: shipped to production, merged to `dev` but not yet released, or still on a branch. Handles repos whose `main` and `dev` histories diverged permanently, and flags a PR that reads as merged while its sha is nowhere in `main`. |
| `clio-echo` | The reading half of `clio-brownbook`, meant for a personal-secretary agent that cannot reach your machine. Reads the finished weekly note out of the log repo and answers from it; nudges on Friday when the week is still empty. Named for the nymph who could only repeat what others had already said — it writes nothing, and holds no raw material to invent from. Needs one fine-grained token scoped to the log repo with `Contents: Read`; it can reach no other repository. |

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
    ├── clio-brownbook/
    │   ├── SKILL.md                              # how to collect, read and write; note shape lives in the log repo
    │   └── scripts/
    │       ├── collect.py                        # gathers PRs, issues, commits, typed prompts -> JSON
    │       ├── outline.py                        # compact views of that JSON, so the full file is never read
    │       ├── redact.py                         # strips PR bodies and typed prompts, for the copy the reader may see
    │       └── publish.sh                        # pushes note + redacted data to a private log repo
    └── clio-echo/
        ├── SKILL.md                              # read-only rules: answer from the note, never invent
        └── scripts/
            └── read_log.py                       # fetches notes from the log repo (stdlib only, no deps)
```

To add a new skill, create `skills/<name>/SKILL.md` and `npx skills` will discover it automatically.
