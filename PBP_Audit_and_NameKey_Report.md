# Play-by-Play Audit + the Name-Key Bug (Bug #5)

Two findings. The first is good news. The second is not, and it is in the **current
paper**, not the proposed play-by-play work.

---

## Part 1 — The play-by-play data is trustworthy. Use it.

Source: `ramirobentes/nba_pbp_data`, `lineup-final{2022..2026}` directories.

| Check | Result |
|---|---|
| Seasons | All five, **including 2025-26** (which `shufinskiy/nba_data` lacks — it stops at 2024/25) |
| Games per season | 1230 × 5 |
| Games per team | Exactly 82, all 30 teams, all seasons |
| Lineup integrity | Every lineup exactly 5 players |
| Season labelling | End-year. `2026` = game-ids `00225…`, dates 2025-10-21 → 2026-04-12 |
| Team codes | `BKN / CHA / PHX` — matches roster tags, **not** the per-game files (`BRK/CHO/PHO`) |
| Net ratings rebuilt from stints | League mean **+0.046** (≈0, as it must be); OKC +11.1 high, WAS −11.9 low |
| **Starters vs `NBA_Starting_Lineups_2025-26`** | **2460 / 2460 joined. 98.05% exact. 100% of the residual is name encoding — zero real lineup disagreements.** |

**The schema hands you the identification ladder almost for free:**
- `lineup-final` is already stint-level **with `lineup_opp` attached** → rung 3 (opponent
  adjustment) needs no construction.
- `pbp-final` carries `margin_before` and a precomputed `garbage_time` flag → rung 2.
- Lineups are stored as **numeric `player_id`**, not names.

### Repository caveats (must be pinned)
- The `pbp-final-*` **directory** CSVs are **partial** — `pbp-final-2024/data.csv` holds
  **103 games**, not 1230. Full pbp is in the **release assets** only, and release coverage
  is uneven (`pbp-final`: 2022/2023/2026; `possessions`: 2022–2024).
- The `lineup-final` **directories** *are* complete for all five seasons. Those are what
  `pbp_preflight.py` uses.
- 24 stars, 1 fork. Not battle-tested. Hence the preflight.

---

## Part 2 — Bug #5: the name-key bug, and it is in the ORIGINAL analysis

The pipeline keys players on `"first-initial. surname"`. Both loaders build dicts:

```python
tags[team][nm]   = tag     # collision -> SILENT OVERWRITE
posmap[team][key] = pos    # collision -> SILENT OVERWRITE
```

A collision does not raise. It overwrites, and a player disappears.

The roster-tag sheet tries to dodge this by **extending the initial** — `Jal. Williams` vs
`Jay. Williams`, `Ste. Curry`, `Jef. Green`. But **no other sheet follows that convention.**
The same player is carried under **four incompatible naming schemes**:

| Sheet | Jalen Williams (OKC) | Jaylin Williams (OKC) |
|---|---|---|
| Roster Tags | `Jal. Williams` | `Jay. Williams` |
| 5ML lineup strings | **`Jay. Williams`** | **`Jay. Williams`** |
| Per-game positions | **`J. Williams`** | **`J. Williams`** |
| Grid (starters) | `J. Williams` / `Jal. Williams` | `Jay. Williams` |

### Consequence A — corrupted 5ML lineups
**376 lineup rows / 2,144 minutes / 8 team-seasons** contain a lineup string in which one
name covers two different players. Real example, OKC 2022-23:

```
S. Gilgeous-Alexander - L. Dort - J. Giddey - Jay. Williams - Jay. Williams
  289 min, NetRtg -2.1, labelled "Short Bench Pilfered"   (PILFER bundle)
```

The true five are SGA (ST), Dort (ST), Giddey (ST), **Jalen Williams (ST)**, Jaylin
Williams (DB) = **4 Starters + 1 Deep Bench = "Starters + Deep Bench Player" = PRESERVE
bundle.** 289 minutes sit in the wrong side of the headline metric.

Affected team-seasons: OKC ×4, HOU ×2, DEN 2021-22, GSW 2025-26.

### Consequence B — starters silently dropped from Finding 3.9
Tagged Starters whose position does not resolve, so their position drops out of the
by-position league average:

| Season | Team | Player | GP / GS |
|---|---|---|---|
| 2021-22 | DEN | Jeff Green | 75 / 63 |
| 2022-23 | OKC | Jalen Williams | 75 / 62 |
| 2023-24 | OKC | Jalen Williams | 71 / 71 |
| 2024-25 | HOU | Jalen Green | **82 / 82** |
| 2025-26 | GSW | **Stephen Curry** | 43 / 41 |
| 2025-26 | OKC | Jalen Williams | 33 / 33 |

Finding 3.9's kept-team counts (109 / 98 / 96 / 99 / 116) are wrong by these.

### Consequence C — a whole team-season is mis-tagged
**HOU 2023-24** has exactly one Green in the tag list:

```
'j. green' -> tag = GT (Garbage Time), GP/GS = (0, 0)
```

Jalen Green started ~76 games that season. He is tagged as a **garbage-time player with
zero games played**, and Houston shows only **4 tagged Starters**. Every lineup containing
him is misclassified. The team-season is in the 150.

The convention is also **inconsistent across seasons**: 2023-24 collapses both Greens into
one entry; 2024-25 splits them (`jal. green` / `jef. green`). So the bug appears and
disappears year to year.

### Consequence D — homoglyphs
`E. Dёmin` (BKN 2025-26) is carried three ways: Cyrillic **ё** (U+0451), Cyrillic **е**
(U+0435), and Latin `E. Demin` in the 5ML strings. `norm()` ASCII-folds the Cyrillic away
to `e. dmin`. **This is currently harmless** — every name-keyed source uses a Cyrillic
variant, so they fold consistently. But the play-by-play spells him `Egor Demin` (Latin),
which folds to `e. demin`. Any name-based join to external data misses him — 45 starts.

---

## How much does this move the paper?

| Quantity | Effect |
|---|---|
| **Pooled NRG (+1.60)** | Dropping all 376 corrupted rows moves it to **+1.575** — a **−0.022** change. **The headline is safe.** |
| Team-level NRG | **Materially wrong** for OKC (all four seasons), HOU 2023-24, HOU 2024-25, DEN 2021-22, GSW 2025-26 |
| **Finding 3.9** | Kept-team counts wrong; six starters (incl. Curry, Jalen Green) silently excluded |
| Tag counts (177/196/180/108) | Wrong for the affected team-seasons |
| OKC 2022-23 = 82 games w/ non-Starter | Still correct — but for the *wrong reason* (it reads 4 tagged Starters because Jalen Williams collides out) |

**The good news is real:** +1.60 survives, and the sign and the story survive. The
by-position level (+3.1 to +3.9, all positive) is not plausibly at risk from ~0.36% of
minutes. What is at risk is anything **team-level** and anything that depends on
**4S+1DB minutes** — which is precisely Finding 3.9's calculability rule.

---

## The fix — for both pipelines

**Re-key everything on `player_id`.** This is not a play-by-play nicety; it retires an
entire *class* of bug that has now hit this project five times (base_v2, name-collision,
team-abbreviation, name-suffix, and this).

1. **Build the bridge once.** `pbp_preflight.py` already does it: 3,293 player-team-seasons
   mapped from `player_id` → roster-tag key, with 3 unmatched (two-ways/10-days, expected)
   and **1 hard collision** (HOU 2023-24 `j. green` ← Jalen Green + Jeff Green) that the
   tool refuses to pass.
2. **Fix the position map first — it is the cheapest, highest-value repair.**
   `load_positions()` *deliberately abbreviates* the full name it already has:
   ```python
   key = norm(parts[0][0] + '. ' + ' '.join(parts[1:]))   # 'Jalen Williams' -> 'j. williams'
   ```
   The per-game file contains `Jalen Williams` and `Jaylin Williams` in full. The
   information is there and the code is throwing it away. Key on the full name (or the
   bridged id) and Consequence B disappears — including Curry.
3. **Regenerate the 5ML lineup strings with ids.** This is the only fix for Consequence A;
   the ambiguity is baked into the workbook and cannot be recovered from the string.
4. **Re-derive HOU 2023-24 tags.** Consequence C is a data error, not a code error.
5. **Add these as assertions**, so they fail loudly forever after.

---

## Suggested sequencing

1. Run `pbp_preflight.py`. It must pass before anything is built on the play-by-play.
2. Fix `load_positions()` to key on full name → re-run `verify_all.py` → **expect Finding
   3.9's kept-team counts and possibly the +3.3/+3.1/+3.1/+3.9/+3.7 values to move.**
   (This is the finding we shipped today. It should be re-checked before submission.)
3. Re-derive HOU 2023-24 roster tags.
4. Only then start the identification ladder.

The pooled headline is robust. The positional finding is the one to re-verify.
