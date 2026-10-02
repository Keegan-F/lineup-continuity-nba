# The Value of Lineup Continuity in the NBA

Replication data and code for the research paper **"The Value of Lineup Continuity in the NBA"**
(Jim Fleigner & Keegan Fleigner, Impact Consultancy LLC), submitted to the MIT Sloan Sports
Analytics Conference.

This repository contains the data used to conduct the research and the code used to validate and
reproduce the headline results, in keeping with the conference's open-source submission guidelines.

---

## What the research asks

When a starter is unavailable (injury or rest), the coach chooses between two strategies:

- **Pilfer** the bench — promote a stronger Short Bench player (e.g., the sixth man) into the
  starting five, weakening bench cohesion.
- **Preserve** the bench — start a Deep Bench player instead, keeping the bench unit intact at the
  cost of immediate starting-lineup talent.

We measure which strategy produces better on-court results, per team and league-wide, using the
**Net Ratings Gap (NRG)** = (Preserve-bundle net rating) − (Pilfer-bundle net rating). A positive
NRG means preserving bench continuity outperformed pilfering it.

**Scope:** five seasons (2021-22 through 2025-26), all 30 teams, 150 team-seasons.

---

## Headline result

- **Pooled NRG ≈ +1.6** net-rating points: across the league, preserving bench continuity
  outperformed pilfering it. The effect is robust across seasons and clears zero.
- The headline was independently **reproduced from play-by-play** data (≈ +1.61; 150 team-season
  NRGs correlate at **r = 0.98** with the workbook results), and a **role-epoch refinement** that
  allows a player's tag to change mid-season when his role durably changes nudges the pooled figure
  to **≈ +1.85**. Both are documented in `/docs`.

---

## Repository layout

```
data/
  source/     Raw input data (all publicly sourced — see "Data sources & privacy" below)
  derived/    Outputs produced by our pipeline (tag maps, NRG results, pivot workbooks)
code/         Python used to validate, reconcile, and reproduce the results
figures/      Figures from the paper
docs/         Methodology notes, data-integrity audits, and finding write-ups
DATA_DICTIONARY.md   Field-level description of every data file
```

### `data/source/`
| File | What it is | Public source |
|---|---|---|
| `NBA_RosterTags_5ML_{season}.xlsx` | Per-player roster tags (Starter / Short Bench / Deep Bench / Garbage Time) derived from availability, plus per-team five-man-lineup (5ML) net ratings | Derived from NBA.com & Basketball-Reference box scores |
| `NBA_Starting_Lineups_{season}.xlsx` | Per-game starting five, opponent, result, score | Basketball-Reference |
| `NBA_Lineups_Advanced_{season}_byTeam.xlsx` | Five-man-lineup advanced stats by team | NBA.com Stats |
| `NBA_Player_PerGame_{season}_byTeam.xlsx` | Per-game player box-score aggregates | Basketball-Reference |
| `NBA_Injuries_2021-2025_combined.xlsx` | Injury/absence report spells by player | Public injury reports (Pro Sports Transactions style) |
| `NBA_Transactions_2021-2026_bySeason.xlsx` | Roster moves (trades, signings, waivers, IR) | Basketball-Reference transactions |
| `nba_rosters_salaries_contract_type_2021-2026.xlsx`, `nba_player_base_salaries_2021-2026.xlsx` | Base salaries and contract types | Public salary data (Spotrac / Basketball-Reference) |

> **Play-by-play.** Stint-level play-by-play (every five-man lineup's possessions and points) is
> **not redistributed here** because it is a large public dataset maintained by a third party. It is
> freely available at **`github.com/ramirobentes/nba_pbp_data`** (the `lineup-final` files). Our
> code reads those files as `lineup_{2022..2026}.csv` (season = end-year). See
> `docs/PBP_Audit_and_NameKey_Report.md` for how we validated them.

### `data/derived/`
| File | What it is |
|---|---|
| `scenario_lookup.json` | The (ST,SB,DB,GT) tag-composition → scenario rule, validated against 81,311/81,311 clean lineups |
| `player_id_bridge.json` | Maps roster-tag name strings → stable play-by-play `player_id` (3,293 entries); the key to collision-safe analysis |
| `franchise_wins_final.json` | Five-year franchise table: NRG, flexible-minute share, wins/season |
| `hou_corrected_row.json`, `hou_2023-24_corrected_tags.json`, `corrected8_nrg.json` | The name-collision ("Bug #5") corrections |
| `NBA_Continuity_MinuteDistribution.xlsx` | All 30 teams × 5 seasons: minute distribution by scenario and by starting class |
| `NBA_PlayByPlay_Stints_Pivots.xlsx` | ~374k raw play-by-play stints with derived tags/scenarios + per-season pivots |
| `LAClippers_*.xlsx` | A fully worked single-team example (game-by-game, lineup-by-lineup, tag-composition) |

### `code/`
| File | Purpose |
|---|---|
| `continuity_lib.py` | Core library: loads roster tags, positions, 5ML data; scenario classification; NRG computation |
| `pbp_preflight.py` | 77-check integrity gate on the play-by-play (game counts, clock/possession invariants, score & starter reconciliation, ID bridge) |
| `verify_all.py` | 63-check regression gate on the headline results |
| `make_charts.py` | Regenerates the paper's figures |
| `split_minutes.py`, `misattr2.py`, `sweep_step.py` | Supporting analyses (name-collision minute-split, bundle misattribution, threshold sweep) |

Code submission is optional under the guidelines; we include it to support reproducibility.

---

## Reproducing the results

**One command** (from the repository root):

```bash
bash reproduce.sh
```

This installs dependencies, fetches the play-by-play from its public source, validates it, and
runs the headline + regression checks. Step by step, if you prefer:

```bash
# 1. Python 3.10+ dependencies
pip install -r requirements.txt

# 2. Fetch the play-by-play (public, not redistributed here) into ./pbp/
python fetch_pbp.py          # pulls lineup_2022.csv ... lineup_2026.csv

# 3. Tell the scripts where the data lives (reproduce.sh sets these for you)
export CONTINUITY_DATA="$(pwd)/data/source"
export PBP_DATA="$(pwd)/pbp"

# 4. Validate the play-by-play against the box-score sources (77-check gate)
python code/pbp_preflight.py

# 5. Reproduce the headline and regression checks (63-check gate)
python code/verify_all.py

# optional: regenerate the paper's figures
python code/make_charts.py
```

> `fetch_pbp.py` tries a few known upstream paths; if `ramirobentes/nba_pbp_data` reorganizes,
> download the five `lineup-final` CSVs manually and save them as `pbp/lineup_{2022..2026}.csv`
> (season label = end-year). The scripts also auto-discover data under common locations, so setting
> the two environment variables is belt-and-suspenders, not strictly required.

The pipeline is deterministic; there is no random seeding or model training. "Reproducible" here means
the arithmetic — tag assignment, scenario classification, minute-weighted net ratings, and the NRG
subtraction — can be re-derived exactly from the source data.

---

## Data sources & privacy

All data in this repository is **public information about professional athletes in their public
professional capacity** — box scores, lineups, public injury/transaction reports, and publicly
reported salaries (NBA.com, Basketball-Reference, Spotrac). Per the submission guidelines we reviewed
the data for personal information requiring anonymization and found **none**: there are no contact
details, government identifiers, medical records beyond public injury designations, or any
non-public personal data. Player and team names are retained because they are public and because the
research is not interpretable without them (team- and player-level findings are the point). No
anonymization was therefore applied; this decision is documented here deliberately rather than
omitted.

---

## A note on data integrity (why `player_id` matters)

A subtle but consequential defect ("Bug #5") shaped our methodology: when two players on the same
team share a first initial and last name (e.g. Jalen/Jaylin Williams, Jeff/Jalen Green,
Stephen/Seth Curry), name-keyed joins silently merge or misattribute their minutes, corrupting eight
team-seasons. **All analyses in this repository key on the stable play-by-play `player_id`**, never on
name strings, and the Houston 2023-24 Green tags are corrected accordingly. See
`docs/PBP_Audit_and_NameKey_Report.md`, `docs/Bug5_TeamSeason_Analysis.md`, and
`docs/Collision_MinuteSplit_and_Misattribution.md`.

---

## Citation

> Fleigner, J. & Fleigner, K. *The Value of Lineup Continuity in the NBA.* Impact Consultancy LLC.
> Submitted to the MIT Sloan Sports Analytics Conference.

## License

Code is released under the MIT License (see `LICENSE`). Source data remains subject to the terms of
its original public providers; it is included here for replication only.
