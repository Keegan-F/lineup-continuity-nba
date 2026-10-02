# Data Dictionary

Field-level description of the data files. Seasons are labelled by span (e.g. `2023-24`); where a
single year appears it is the season **end-year** unless noted (the play-by-play convention).

---

## `data/source/`

### `NBA_RosterTags_5ML_{season}.xlsx`
The central input. Multiple sheets per file.

**`Roster Tags` sheet** — one row per player-team-season:
| Column | Description |
|---|---|
| `Player-Team` | Player name + team code (e.g. `J. Harden-BKN`) |
| `Team` | Team code (e.g. `BKN`, `LAC`) |
| `GP`, `GS` | Games played, games started |
| `Rostered Games` | Games the player was on the active roster |
| `Non-Rostered Games` | Games not on roster (trade, 10-day, G-League, etc.) |
| `Injured Games`, `Inactive Games` | Games missed by reason |
| `Eligible Games` | Games available to play = Rostered − Injured |
| `GP%`, `GS%` | Availability-adjusted rates: GP/Eligible, GS/Eligible |
| `Roster Tag` | **ST** (Starter), **SB** (Short Bench), **DB** (Deep Bench), **GT** (Garbage Time) |

Tag rule (availability-based): **ST** if GS% ≥ 0.58 and GP% ≥ 0.90; else **SB** if GP% ≥ 0.85;
else **DB** if GP% ≥ 0.35; else **GT**.

**Per-team sheets** (`ATL`, `ATL Summary`, …) — each team's five-man lineups with minutes and net
ratings, plus a summary. **`League NRG Summary`** — the per-team NRG table.

> **Collision caveat:** name strings in these files use first-initial + last name and cannot
> distinguish two same-name players on one team. The analysis resolves this via
> `data/derived/player_id_bridge.json`; see the README's data-integrity note.

### `NBA_Starting_Lineups_{season}.xlsx`
One sheet per team (codes `BRK`/`CHO`/`PHO` for Brooklyn/Charlotte/Phoenix). One row per game:
`G`, `Date`, `Home/Away`, `Opponent`, `Result`, `Tm Pts`, `Opp Pts`, `Wins`, `Losses`,
`Starter 1`…`Starter 5`.

### `NBA_Lineups_Advanced_{season}_byTeam.xlsx`
NBA.com advanced five-man-lineup stats by team (net rating, possessions, minutes).

### `NBA_Player_PerGame_{season}_byTeam.xlsx`
One sheet per team; standard per-game box-score columns (`Rk, Player, Age, Pos, G, GS, MP, FG …`).
`Pos` is the position label used in the position analyses (PG/SG/SF/PF/C).

### `NBA_Injuries_2021-2025_combined.xlsx`
One sheet per season, labelled by **start-year** (sheet `2023` = the 2023-24 season). Each row is a
player; injury spells are stored as paired `Start`/`End` date columns (text `M/D/YY`). The parser in
the analysis reads these pairs. Names are first-initial + last-name form.

### `NBA_Transactions_2021-2026_bySeason.xlsx`
One sheet per season span. Columns: `Date`, `Team`, `Player` (full name), `Position`, `Transaction`
(free text — trades, signings, waivers, IR placements, "will miss remainder of season" notices).

### `nba_rosters_salaries_contract_type_2021-2026.xlsx`
`Roster + Salary (Long)` sheet: `Season, Player, Teams, Pos, G, Base Salary, Two-Way Salary (est.),
Contract Type`. Used for the cost comparison (Deep Bench vs Short Bench) and as a contract-tier
error-check on tags.

### `nba_player_base_salaries_2021-2026.xlsx`
Wide form: one row per player, a base-salary column per season.

---

## `data/derived/`

### `scenario_lookup.json`
Maps a tag composition `"ST,SB,DB,GT"` (counts summing to 5) → scenario name:
`Starter Baseline`, `Starters + Short Bench Player`, `Starters + Deep Bench Player`,
`Short Bench Preserved`, `Short Bench Pilfered`, `Garbage Time`. Validated against 81,311/81,311
clean lineups.

- **Preserve bundle** = `Starters + Deep Bench Player` + `Short Bench Preserved`
- **Pilfer bundle** = `Starters + Short Bench Player` + `Short Bench Pilfered`
- **NRG** = Preserve net rating − Pilfer net rating

### `player_id_bridge.json`
`{ "season|team|name_string": player_id }` — 3,293 entries linking roster-tag names to stable
play-by-play `player_id`s. The mechanism that makes the analysis collision-safe.

### `franchise_wins_final.json`
Per team: `nrg` (5-yr avg Net Ratings Gap), `flexshare` (share of minutes in flexible preserve/pilfer
lineups), `wins` (= nrg × flexshare ÷ 2.7, the Pythagorean points-per-win conversion).

### `hou_2023-24_corrected_tags.json`, `hou_corrected_row.json`, `corrected8_nrg.json`
The name-collision corrections. HOU 2023-24: Jalen Green = ST, Jeff Green = SB (the name-keyed data
had mislabeled Jalen Green as Garbage Time). `corrected8_nrg.json` holds the eight affected
team-seasons.

### Workbooks
- `NBA_Continuity_MinuteDistribution.xlsx` — 30 teams × 5 seasons; % of minutes by scenario and by
  starting class, with underlying minutes.
- `NBA_PlayByPlay_Stints_Pivots.xlsx` — ~374k play-by-play stints with derived tag composition,
  scenario, and game starting class, plus per-season and combined pivots.
- `LAClippers_Continuity_Workbook.xlsx`, `LAClippers_PlayByPlay_Stints_Pivots.xlsx` — a fully worked
  single-team example at game, lineup, and tag-composition granularity.

---

## Play-by-play (external)

Source: `github.com/ramirobentes/nba_pbp_data`, `lineup-final` files, read as `lineup_{2022..2026}.csv`
(season = end-year). Stint-level columns: `game_id, location_team, period, stint, team, opp,
lineup_team, lineup_opp, secs_game_start, secs_game_end, secs_played, poss_team, pts_team, poss_opp,
pts_opp`. Lineups are stored as `"player_id FullName"` pairs — the `player_id` is what the bridge keys
on. Validated by `code/pbp_preflight.py` (see `docs/PBP_Audit_and_NameKey_Report.md`).
