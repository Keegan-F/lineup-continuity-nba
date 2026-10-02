# Same-Name Collisions — Minute Split & Bundle Misattribution

The 8 team-seasons where two players on one team share a first-initial + last name. All
figures are derived from **play-by-play keyed on player_id** (ramirobentes lineup-final),
which is the source of truth for these cases going forward. Where the roster-tag list itself
was broken (HOU 2023-24), the re-derived tags are used (Jalen Green ST, Jeff Green SB).

---

## 1. How the shared-name minutes actually split between the two players

The workbook logged both players under one name string. From play-by-play, those on-court
minutes divide as follows — always toward the player who played and started more:

| season | team | shared name | higher-usage player (GP/GS) | share | other player | share |
|---|---|---|---|---:|---|---:|
| 2021-22 | DEN | J. Green | Jeff Green (75/63) | 63.0% | JaMychal Green | 37.0% |
| 2022-23 | OKC | J. Williams | Jalen Williams (75/62) | 71.3% | Jaylin Williams | 28.7% |
| 2023-24 | HOU | J. Green | Jalen Green (82/82) | 66.6% | Jeff Green | 33.4% |
| 2023-24 | OKC | J. Williams | Jalen Williams (71/71) | 71.3% | Jaylin Williams | 28.7% |
| 2024-25 | HOU | J. Green | Jalen Green (82/82) | 87.2% | Jeff Green | 12.8% |
| 2024-25 | OKC | J. Williams | Jalen Williams (69/69) | 74.0% | Jaylin Williams | 26.0% |
| 2025-26 | GSW | S. Curry | Stephen Curry (43/41) | 90.9% | Seth Curry | 9.1% |
| 2025-26 | OKC | J. Williams | Jaylin Williams (65/11) | 57.7% | Jalen Williams | 42.3% |

The split runs from ~63/37 to ~91/9, widening with the usage gap (Stephen vs Seth Curry is
the most lopsided pairing and the most lopsided split). This is **not 50/50 noise** — it is
a systematic majority of one specific player's minutes.

**One inversion to note:** in 2025-26 OKC the higher-*minutes* player is Jaylin Williams
(65 GP but only 11 GS), while Jalen Williams played just 33 games (all starts) due to limited
availability. The minute share correctly follows total floor time (Jaylin), even though
Jalen started a higher fraction of his own games. In the other seven, the more-available
player is unambiguously the higher-minute one.

---

## 2. Why the split causes damage: bundle misattribution

Because the higher-usage player usually carries a **different tag** than his namesake
(ST vs DB, ST vs SB), collapsing them makes the workbook miscount the number of Starters on
the floor — and Starter-count is exactly what determines a lineup's preserve/pilfer/baseline/
garbage bundle. Result: a large share of each collision's minutes were filed in the wrong
bundle.

Of the minutes in **corrupted workbook lineup rows** (one name covering two players):

| season | team | corrupt min | wrong bundle | % wrong | net bundle shift |
|---|---|---:|---:|---:|---|
| 2021-22 | DEN | 198 | 149 | **75.3%** | preserve −79, pilfer +149 |
| 2022-23 | OKC | 655 | 330 | **50.4%** | **preserve +289**, pilfer −248 |
| 2023-24 | HOU | 620 | 310 | **50.0%** | preserve +262, pilfer −167 |
| 2023-24 | OKC | 247 | 0 | 0.0% | none (see below) |
| 2024-25 | HOU | 156 | 67 | 42.9% | preserve +51, pilfer −35 |
| 2024-25 | OKC | 172 | 60 | 34.9% | preserve −25, pilfer +47 |
| 2025-26 | GSW | 17 | 2 | 11.8% | negligible |
| 2025-26 | OKC | 79 | 21 | 26.6% | preserve −19, pilfer +20 |

Between one-third and three-quarters of every collision's minutes were misfiled — with one
genuine exception.

### The dominant flows (opposite directions)

- **OKC 2022-23 — 289 min Pilfer → Preserve.** The SGA-Dort-Giddey-Jalen-Jaylin lineup:
  with both Williamses correctly resolved as ST + DB, it is a true 4S+1DB *Preserve* lineup
  that the workbook had buried in Pilfer. This one *helps* preserve.
- **HOU 2023-24 — 262 min into Preserve.** Driven by the phantom-GT fix: once Jalen Green
  is correctly ST, lineups the workbook called garbage/pilfer become real preserve/baseline
  minutes.

### The genuine zero: 2023-24 OKC

Jalen Williams started all 71 of his games, so in every corrupted row the true composition
was 1 ST + 1 SB — the same Starter-count the workbook assumed. The bundle is unchanged
regardless of which Williams is named. Misattribution requires the two players' tags to
differ enough to change the count of Starters on the floor; here they effectively didn't.

---

## 3. Method & caveat

- Minute split: exact, from play-by-play `secs_played` summed by `player_id`.
- Bundle misattribution: each corrupted workbook row's minutes are compared between the
  scenario the workbook assigned and the true scenario(s) from play-by-play. Where one
  corrupted row spans multiple true compositions, its minutes are distributed across the
  true scenarios by their play-by-play proportion (a single workbook aggregate cannot be
  split any other way). **Bundle directions and the ~% wrong are solid; the exact minute
  counts within a multi-composition row carry that proportional assumption.**
- The 100%-verified scenario lookup (`scenario_lookup.json`) maps (ST,SB,DB,GT) composition
  to scenario; validated against 81,311/81,311 clean workbook lineups.

## Files
- `split_minutes.py` — the minute-split computation
- `misattr2.py` — the bundle-misattribution computation
- `scenario_lookup.json` — the composition → scenario rule
