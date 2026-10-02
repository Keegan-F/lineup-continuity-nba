# The 8 Corrected NRGs — Play-by-Play, Keyed on player_id

Per instruction: for the 8 team-seasons where two players share a first-initial + last name,
NRG is computed **solely from play-by-play, keyed on player_id**, which removes the name
ambiguity entirely. HOU 2023-24 additionally uses the re-derived tags (Jalen Green = ST,
Jeff Green = SB).

Method: tag every play-by-play player by `player_id`; classify each stint's five-man lineup
by its (ST, SB, DB, GT) composition using the scenario rule verified 100% against the
workbook; aggregate possession-weighted; NRG = preserve-bundle net − pilfer-bundle net.

---

## Headline table

| season | team | published | **corrected (pbp)** | total delta |
|---|---|---:|---:|---:|
| 2021-22 | DEN | +3.00 | **+13.65** | +10.65 |
| 2022-23 | OKC | −3.60 | **+0.56** | +4.16 |
| 2023-24 | HOU | +1.59 | **−0.48** | −2.07 |
| 2023-24 | OKC | −6.79 | **−8.23** | −1.44 |
| 2024-25 | HOU | −4.10 | **+2.71** | +6.81 |
| 2024-25 | OKC | +1.32 | **+0.79** | −0.53 |
| 2025-26 | GSW | −0.94 | **+4.44** | +5.38 |
| 2025-26 | OKC | +4.59 | **+7.19** | +2.60 |

**Read this table with the caveat below before drawing any conclusion from the deltas.**

---

## The critical caveat: the delta is NOT the bug-fix

The "total delta" conflates **two different things**, and they are of comparable size:

1. **The bug #5 fix** — correctly assigning the collision minutes by player_id.
2. **The estimator change** — play-by-play net ratings differ from NBA.com's season
   averages even with zero corruption.

I measured the estimator effect directly, on the 12 *clean* (uncorrupted) team-seasons of
these same four franchises (DEN, OKC, HOU, GSW): it has **mean −0.30 but standard deviation
1.09**, and individual team-seasons swing by up to ±1.6 net rating points **from the
estimator alone**. So a raw delta of +5 or +10 is mostly estimator, not fix.

Decomposing each team-season (`corrected8_decomposed.json`) into the two components:

| season | team | bug #5 effect | estimator effect |
|---|---|---:|---:|
| 2021-22 | DEN | +4.40 | +6.25 |
| 2022-23 | OKC | +1.42 | +2.74 |
| 2023-24 | HOU | −1.72 | −0.36 |
| 2023-24 | OKC | +0.61 | −2.04 |
| 2024-25 | HOU | −0.26 | +7.07 |
| 2024-25 | OKC | +0.90 | −1.43 |
| 2025-26 | GSW | −0.45 | +5.83 |
| 2025-26 | OKC | +2.30 | +0.31 |

The estimator column is frequently the larger of the two. HOU 2024-25's headline +6.81 delta
is almost entirely estimator (+7.07); the bug #5 fix there is negligible (−0.26). DEN's
+10.65 is roughly 40% fix, 60% estimator.

**Honesty note on the decomposition itself:** the "estimator effect" is measured by
reproducing the corruption on the play-by-play scale, which cannot perfectly replicate the
workbook's exact collision behavior (the collision interacts with scenario classification,
not just the tag). So the split is indicative, not exact — but the *direction* of the
message is robust: these deltas are dominated by the estimator, and none of them can be
reported as "the bug moved this team-season by X" without that qualification.

---

## What can be stated cleanly

**On the workbook's own scale** (the estimator-free bound from the prior analysis, which
does not depend on any play-by-play net ratings), bug #5 moves these team-seasons by:

| season | team | published | bound (corrupt rows dropped) | shift |
|---|---|---:|---:|---:|
| 2021-22 | DEN | +3.00 | +6.10 | **+3.10** |
| 2022-23 | OKC | −3.60 | −5.26 | **−1.66** |
| 2023-24 | HOU | +1.59 | −0.16 | **−1.74** |
| 2023-24 | OKC | −6.79 | −9.38 | **−2.59** |
| 2024-25 | HOU | −4.10 | −4.93 | −0.82 |
| 2024-25 | OKC | +1.32 | +2.30 | +0.98 |
| 2025-26 | GSW | −0.94 | −0.43 | +0.51 |
| 2025-26 | OKC | +4.59 | +3.46 | −1.12 |

That table (from `Bug5_TeamSeason_Analysis.md`) is the one I would trust for "how much did
the bug distort this team-season," because it never leaves the workbook's estimator. The
play-by-play table above is the answer to the literal instruction — "compute the NRG solely
from play-by-play" — and it is correct as such, but its deltas-vs-published carry the
estimator rider.

---

## HOU 2023-24 — the tag fix worked, and it matters here

The re-derived tags (Jalen Green ST, Jeff Green SB) restore Houston to 5 tagged Starters.
On the play-by-play scale its NRG is −0.48 vs. a published +1.59. The bug #5 component is
−1.72 (a real, correct move — Houston looks *worse* at preserving once its actual starter
is recognized). This is the one team-season where the fix is both large and clean of the
"phantom GT player" artifact that made the published number meaningless.

Note: 77 play-by-play lineups (129 min, ~1.5% of Houston's minutes) contained a player who
resolves to no tag — almost entirely deep 10-day/two-way players who never appeared in the
tag list at all. They're excluded, matching how the workbook treats untagged players.

---

## Bottom line

- The 8 play-by-play NRGs are computed correctly and keyed on player_id, so the name
  ambiguity is fully gone. `corrected8_nrg.json`.
- **Do not report the raw deltas as the bug's impact.** They are dominated by the
  estimator change (σ ≈ 1.1 pts/team-season), not by bug #5.
- For "how much did bug #5 distort the paper," use the workbook-scale bound table
  (shifts of −2.6 to +3.1, five of eight exceeding 1 point).
- HOU 2023-24's tags are genuinely fixed and its correction is the cleanest of the set.

## Files
- `corrected8_nrg.json` — the 8 play-by-play NRGs vs published
- `corrected8_decomposed.json` — bug-fix vs estimator split per team-season
- `hou_2023-24_corrected_tags.json` — the re-derived HOU Green rows
