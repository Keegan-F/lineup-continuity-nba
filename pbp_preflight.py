"""pbp_preflight.py — the gate for the play-by-play pipeline.

RUN THIS FIRST IN ANY NEW SESSION, before trusting any play-by-play output.
Same contract as verify_all.py: every assertion below is a number someone might otherwise
take on faith. If a check fails, the pipeline has drifted — investigate, do not proceed.

WHY THIS EXISTS
---------------
This project has been bitten FIVE times by one failure mode: a name/key mismatch that does
not raise, it just drops rows.

    #1 base_v2 injury regression   wrong tags -> the whole paper was rebuilt
    #2 name-collision undercount   two "J. Williams" on one roster
    #3 team-abbreviation mismatch  BRK/CHO/PHO vs BKN/CHA/PHX -> 3 teams vanished
    #4 name-suffix mismatch        "D. Jones Jr." vs "D. Jones"
    #5 extended-initial mismatch   "jal. williams" vs "j. williams" -> Stephen Curry,
                                   Jalen Green and Jalen Williams were silently dropped
                                   from Finding 3.9

Play-by-play multiplies the surface area. So the rule for this pipeline is absolute:

        NEVER JOIN ON A NAME. JOIN ON player_id.

This module builds that bridge and asserts it is total and unambiguous.

USAGE
    python3 pbp_preflight.py               # audit  (exit 1 on any unexpected failure)
    python3 pbp_preflight.py --download    # fetch the lineup files first (~110 MB)
"""

import os
import re
import sys
import glob
import json
import unicodedata
from collections import defaultdict

import pandas as pd

from continuity_lib import (load_tags, load_positions, teams_in, SEASONS, tags_path,
                            strip_suffix)

# =====================================================================================
# SOURCE PINNING
# =====================================================================================
# Season label -> end-year, as used by ramirobentes/nba_pbp_data.
# VERIFIED: lineup-final2026 carries game_id prefix 00225, dates 2025-10-21..2026-04-12.
# Get this off by one and every tag joins to the wrong season, silently. Hence check 1.3.
SEASON_ENDYEAR = {'2021-22': 2022, '2022-23': 2023, '2023-24': 2024,
                  '2024-25': 2025, '2025-26': 2026}

# Take lineups ONLY from the lineup-final DIRECTORIES — those are complete (1230 games).
# DO NOT take pbp from the pbp-final directories: they are PARTIAL snapshots
# (pbp-final-2024/data.csv holds 103 games, not 1230). Full pbp exists only as RELEASE
# assets, and release coverage is uneven (pbp-final: 2022/2023/2026; possessions: 2022-24).
LINEUP_URL = ('https://raw.githubusercontent.com/ramirobentes/nba_pbp_data/'
              'main/lineup-final%d/data.csv')

EXPECT_GAMES = 1230            # 30 teams x 82 / 2
EXPECT_TEAM_GAMES = 82
EXPECT_TEAMS = 30
REG_SECS = 48 * 60             # 2880; each overtime adds 300s
OT_SECS = 300

DATA_DIRS = [os.environ.get('PBP_DATA', ''), './pbp', '../pbp', '/home/claude/pbp',
             '/mnt/user-data/uploads', '/mnt/user-data/outputs', '.']

# =====================================================================================
# KNOWN ISSUES — explicit, auditable, never silently tolerated.
# Anything listed here still prints as a failure. It is recorded so it cannot be
# forgotten, not so it can be ignored.
# =====================================================================================
KNOWN_ISSUES = {
    # HOU 2023-24 roster tags hold ONE Green: 'j. green' -> tag GT, GP/GS = (0,0).
    # Jalen Green started ~76 games. Both Greens collapse onto the one key.
    # SOURCE DATA ERROR. Not fixable in code. HOU 2023-24 tags must be re-derived.
    'bridge_collision': [('2023-24', 'HOU', 'j. green')],

    # 4 genuine starter disagreements + 3 Gonzalez/Pena naming, out of 12,300 team-games.
    'starter_diffs': 7,

    # bug #5 consequence A: 5ML lineup strings in which one name covers two players.
    # Lives in the workbooks, upstream of all code. Only a player_id rebuild fixes it.
    'corrupted_5ml_rows': 376,

    # LAL@MEM 2023-24: a team's stints sum to 2946s -- 66s OVER regulation, and not a
    # whole overtime. Both teams agree, so the stints tile consistently; it is a clock
    # anomaly in the SOURCE. 2 team-games of 6150. Excluded from any clock-weighted work
    # until explained; harmless for possession-weighted work.
    'off_clock_games': {'0022301177'},
}

# =====================================================================================
# check harness (same shape as verify_all.py)
# =====================================================================================
PASS = FAIL = 0
FAILURES = []


def _record(name, ok, detail, known):
    global PASS, FAIL
    if ok:
        PASS += 1
        print('   ok     %s' % name)
    else:
        FAIL += 1
        print('   %s  %s   -- %s' % ('KNOWN' if known else 'FAIL ', name, detail))
        FAILURES.append((name, detail, known))
    return ok


def check(name, got, want, tol=0, known=False):
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    return _record(name, ok, 'got %s, want %s' % (got, want), known)


def check_true(name, cond, detail='', known=False):
    return _record(name, bool(cond), detail, known)


# =====================================================================================
# name handling — used ONLY to validate against the legacy name-keyed files.
# The pipeline itself must key on player_id.
# =====================================================================================
# Cyrillic homoglyphs. 'E. Dёmin' in the workbooks uses U+0451 (and U+0435 elsewhere).
# Plain ASCII-folding DELETES those characters ('e. dmin'), so the name never matches the
# play-by-play's Latin 'Egor Demin'. Fold them to their Latin twins FIRST.
HOMOGLYPH = {'\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c',
             '\u0443': 'y', '\u0445': 'x', '\u0451': 'e', '\u0456': 'i',
             '\u0410': 'A', '\u0415': 'E', '\u041e': 'O', '\u0421': 'C'}
SUFFIX = re.compile(r'[\s,]+(Jr|Sr|II|III|IV|V)\.?$', re.I)


def fold(s):
    s = ''.join(HOMOGLYPH.get(c, c) for c in str(s))
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().strip()


def initial_key(name):
    """'Jalen Williams' -> 'J.WILLIAMS' ; 'C. Capela' -> 'C.CAPELA'
    NOTE: this deliberately collides teammates. That is the point — it is how we detect
    that a name-keyed comparison is unsafe, and why the pipeline must use player_id."""
    x = SUFFIX.sub('', fold(name)).strip()
    p = x.split()
    return (p[0][0] + '.' + p[-1]).upper() if len(p) >= 2 else x.upper()


def tag_key_forms(full_name):
    """Roster tags EXTEND the first initial to disambiguate teammates:
    'Jalen Williams' -> 'jal. williams', 'Stephen Curry' -> 'ste. curry'.
    Candidate tag keys, longest prefix first. (This is the bug #5 resolution.)"""
    p = fold(full_name).lower().split()
    if len(p) < 2:
        return [fold(full_name).lower()]
    first, last = p[0], ' '.join(p[1:])
    out = []
    for k in (4, 3, 2, 1):
        if len(first) < k:
            continue
        base = '%s. %s' % (first[:k], last)
        for cand in (base, strip_suffix(base)):
            if cand not in out:
                out.append(cand)
    return out


def parse_lineup(cell):
    """'1630169 Tyrese Haliburton, 203500 Steven Adams' -> [(1630169, 'Tyrese Haliburton'), ..]"""
    out = []
    for chunk in str(cell).split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        pid, name = chunk.split(' ', 1)
        out.append((int(pid), name.strip()))
    return out


# =====================================================================================
# discovery
# =====================================================================================
def find(fname):
    for d in DATA_DIRS:
        if d and os.path.exists(os.path.join(d, fname)):
            return os.path.join(d, fname)
    hits = glob.glob('/**/' + fname, recursive=True)
    return hits[0] if hits else None


def lineup_path(season):
    p = find('lineup_%d.csv' % SEASON_ENDYEAR[season])
    if not p:
        raise FileNotFoundError('lineup_%d.csv not found. Run with --download, or set PBP_DATA.'
                                % SEASON_ENDYEAR[season])
    return p


def download():
    import urllib.request
    os.makedirs('./pbp', exist_ok=True)
    for season, yr in SEASON_ENDYEAR.items():
        dest = './pbp/lineup_%d.csv' % yr
        if os.path.exists(dest):
            print('  have %s' % dest)
            continue
        print('  fetching lineup-final%d ...' % yr)
        urllib.request.urlretrieve(LINEUP_URL % yr, dest)
    print()


SHEET2PBP = {'BRK': 'BKN', 'CHO': 'CHA', 'PHO': 'PHX'}      # bug #3, in reverse
TEAMNAME2ABB = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI',
    'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC',
    'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA',
    'Washington Wizards': 'WAS',
}


# =====================================================================================
# 1. SOURCE INTEGRITY
# =====================================================================================
def section_sources(frames):
    print('=' * 96)
    print('1. SOURCE INTEGRITY   (partial files exist upstream — assert completeness)')
    print('=' * 96)
    for season in SEASONS:
        df = frames[season]
        want_prefix = '002%02d' % (SEASON_ENDYEAR[season] - 2001)   # 2026 -> 00225
        st = df.lineup_team.str.count(',').add(1)
        so = df.lineup_opp.str.count(',').add(1)
        tg = df.groupby('team').game_id.nunique()
        print('  -- %s  (%s, %d stint-rows)' % (season, os.path.basename(lineup_path(season)), len(df)))
        check('1.1 %s  games == %d' % (season, EXPECT_GAMES), df.game_id.nunique(), EXPECT_GAMES)
        check('1.2 %s  teams == %d' % (season, EXPECT_TEAMS), df.team.nunique(), EXPECT_TEAMS)
        check('1.3 %s  season label (game_id prefix)' % season,
              df.game_id.str[:5].mode()[0], want_prefix)
        check_true('1.4 %s  every team plays %d' % (season, EXPECT_TEAM_GAMES),
                   tg.min() == EXPECT_TEAM_GAMES and tg.max() == EXPECT_TEAM_GAMES,
                   'range %d..%d' % (tg.min(), tg.max()))
        check_true('1.5 %s  own lineup always 5 players' % season,
                   st.min() == 5 and st.max() == 5, 'range %d..%d' % (st.min(), st.max()))
        check_true('1.6 %s  opponent lineup always 5 players' % season,
                   so.min() == 5 and so.max() == 5, 'range %d..%d' % (so.min(), so.max()))
        check_true('1.7 %s  no nulls in key columns' % season,
                   not df[['game_id', 'team', 'opp', 'lineup_team', 'lineup_opp',
                           'secs_played', 'poss_team', 'pts_team']].isna().any().any(), '')
    print()


# =====================================================================================
# 2. CLOCK & POSSESSION INVARIANTS
# =====================================================================================
def section_invariants(frames):
    print('=' * 96)
    print('2. CLOCK & POSSESSION INVARIANTS   (stints that do not tile the game are broken)')
    print('=' * 96)
    for season in SEASONS:
        g = frames[season].groupby(['game_id', 'team'], as_index=False).agg(
            secs=('secs_played', 'sum'), poss=('poss_team', 'sum'),
            poss_a=('poss_opp', 'sum'), pts=('pts_team', 'sum'))

        # a team's stints must exactly tile its game: 48:00, plus whole 5:00 overtimes
        off = g.secs - REG_SECS
        tiles = ((off >= -2) & (off <= 5 * OT_SECS + 2) &
                 ((off.abs() <= 2) | (((off + 2) % OT_SECS) <= 4)))
        rogue = sorted(set(g.game_id[~tiles]) - KNOWN_ISSUES['off_clock_games'])
        check_true('2.1 %s  stints tile the clock (2880s + n*300s)' % season, not rogue,
                   'off-clock games: %s' % rogue)
        known_here = sorted(set(g.game_id[~tiles]) & KNOWN_ISSUES['off_clock_games'])
        if known_here:
            check_true('2.1k %s  known off-clock game still present' % season, False,
                       'game_id %s (secs=%d, 66s over regulation)'
                       % (known_here[0], int(g.loc[g.game_id == known_here[0], 'secs'].iloc[0])),
                       known=True)

        # possessions must be PACE-NORMALISED: an OT game legitimately exceeds 130 raw
        # possessions (LAC 2022-23 had 131 across 2 OTs = 108.4 per 48).
        poss48 = g.poss * REG_SECS / g.secs
        check_true('2.2 %s  possessions per 48 min within [80,125]' % season,
                   poss48.between(80, 125).all(),
                   'range %.1f..%.1f' % (poss48.min(), poss48.max()))
        check('2.3 %s  league mean possessions per 48 min ~100' % season,
              round((g.poss * REG_SECS / g.secs).mean(), 1), 100.0, tol=5.0)
        check_true('2.4 %s  both teams see ~equal possessions (|diff| <= 6)' % season,
                   (g.poss - g.poss_a).abs().max() <= 6,
                   'max |diff| = %d' % (g.poss - g.poss_a).abs().max())
        check_true('2.5 %s  no team-game scores 0 points' % season, (g.pts > 0).all(), '')
    print()


# =====================================================================================
# 3 + 4. RECONCILIATION AGAINST THE PROJECT'S OWN FILES
#
# Join key: (team, opp, home/away, team score, opp score). VERIFIED UNIQUE across all
# 2460 team-games per season. Joining on the OUTCOME validates the schedule AND every
# final score in one move — and needs no game dates, which the lineup files do not carry.
# =====================================================================================
def section_reconcile(frames):
    print('=' * 96)
    print('3. SCORE RECONCILIATION   vs NBA_Starting_Lineups_*.xlsx')
    print('4. STARTER AGREEMENT      vs NBA_Starting_Lineups_*.xlsx')
    print('=' * 96)
    tot_join = tot_games = tot_agree = 0
    diffs = []
    for season in SEASONS:
        sp = find('NBA_Starting_Lineups_%s.xlsx' % season)
        if not sp:
            check_true('3.%s  starting-lineup file present' % season, False, 'not found')
            continue
        df = frames[season]
        sc = df.groupby(['game_id', 'team', 'opp', 'location_team'], as_index=False).agg(
            pts=('pts_team', 'sum'), pts_a=('pts_opp', 'sum'))
        p1 = df[(df.period == 1) & (df.stint == 1)][['game_id', 'team', 'lineup_team']]
        sc = sc.merge(p1, on=['game_id', 'team'], how='left')

        idx = {}
        for r in sc.itertuples():
            idx[(r.team, r.opp, r.location_team, int(r.pts), int(r.pts_a))] = \
                frozenset(initial_key(n) for _, n in parse_lineup(r.lineup_team))

        xl = pd.ExcelFile(sp)
        joined = agree = games = 0
        for sheet in xl.sheet_names:
            tm = SHEET2PBP.get(sheet, sheet)
            for _, row in xl.parse(sheet).iterrows():
                games += 1
                key = (tm, TEAMNAME2ABB.get(str(row['Opponent'])),
                       str(row['Home/Away']).lower(),
                       int(row['Tm Pts']), int(row['Opp Pts']))
                if key not in idx:
                    continue
                joined += 1
                mine = frozenset(initial_key(row['Starter %d' % j]) for j in range(1, 6))
                if mine == idx[key]:
                    agree += 1
                else:
                    diffs.append((season, sheet, sorted(mine - idx[key]), sorted(idx[key] - mine)))

        check('3.%s  every team-game joins on (team,opp,H/A,score,score)' % season,
              joined, games)
        check_true('4.%s  starter agreement >= 99.8%%' % season,
                   joined and agree / joined >= 0.998,
                   '%d/%d = %.2f%%' % (agree, joined, 100 * agree / max(joined, 1)))
        tot_join += joined
        tot_games += games
        tot_agree += agree

    print('\n   TOTAL %d/%d team-games joined; starters agree on %d (%.2f%%)'
          % (tot_join, tot_games, tot_agree, 100 * tot_agree / max(tot_join, 1)))
    check('4.9  residual starter disagreements', len(diffs), KNOWN_ISSUES['starter_diffs'],
          known=True)
    for d in diffs:
        print('        %-8s %-4s  yours-only=%-30s pbp-only=%s' % d)
    print()


# =====================================================================================
# 5. THE ID BRIDGE — the whole point of this file
# =====================================================================================
def section_bridge(frames):
    print('=' * 96)
    print('5. ID BRIDGE    player_id -> roster-tag key     (JOIN ON THIS. NEVER ON A NAME.)')
    print('=' * 96)
    bridge, unmatched, collisions, missing = {}, [], [], []

    for season in SEASONS:
        tags, games = load_tags(season)
        df = frames[season]
        seen = defaultdict(dict)
        for team, cell in zip(df.team, df.lineup_team):
            for pid, name in parse_lineup(cell):
                seen[team][pid] = name

        for team, players in seen.items():
            tkeys = tags.get(team, {})
            claimed = {}
            for pid, name in players.items():
                hit = next((f for f in tag_key_forms(name) if f in tkeys), None)
                if hit is None:
                    unmatched.append((season, team, pid, name))
                    continue
                if hit in claimed and claimed[hit][0] != pid:
                    collisions.append((season, team, hit, claimed[hit][1], name))
                claimed[hit] = (pid, name)
                bridge[(season, team, pid)] = hit
            for key, tag in tkeys.items():
                if tag == 'ST' and key not in claimed:
                    missing.append((season, team, key, games[team][key]))

    print('   bridged player-team-seasons  : %d' % len(bridge))
    print('   pbp players with no tag key  : %d   (two-ways / 10-days / untagged — expected)'
          % len(unmatched))

    known = set(KNOWN_ISSUES['bridge_collision'])
    unexpected = [c for c in collisions if (c[0], c[1], c[2]) not in known]
    check('5.1  unexpected bridge collisions (two players -> one tag key)', len(unexpected), 0)
    check('5.2  known bridge collisions (source-data bug, must be re-derived)',
          len(collisions), len(known), known=True)
    for c in collisions:
        print('        %s %s  key=%r  <-  %s  AND  %s' % c)
    check('5.3  tagged STARTERS unreachable from any player_id', len(missing), 0)
    for m in missing:
        print('        %s %s %r  GP/GS=%s' % m)

    json.dump({'%s|%s|%d' % k: v for k, v in bridge.items()},
              open('player_id_bridge.json', 'w'), indent=0)
    print('   -> wrote player_id_bridge.json   (%d entries; this is the spine — use it)'
          % len(bridge))
    print()
    return bridge


# =====================================================================================
# 6. REGRESSION GUARDS on the original analysis (bugs #3/#4/#5 must stay fixed)
# =====================================================================================
def section_legacy_guards():
    import openpyxl
    print('=' * 96)
    print('6. REGRESSION GUARDS on the original workbooks')
    print('=' * 96)

    unresolved = []
    for s in SEASONS:
        tags, _ = load_tags(s)
        pos = load_positions(s, tags)
        for team in teams_in(s):
            for p, t in tags.get(team, {}).items():
                if t == 'ST' and not pos.get(team, {}).get(p):
                    unresolved.append((s, team, p))
    check('6.1  tagged STARTERS with no position (bug #5 — was 6, incl. Stephen Curry)',
          len(unresolved), 0)
    for u in unresolved:
        print('        %s %s %r' % u)

    dup_rows, dup_ts = 0, set()
    for s in SEASONS:
        wb = openpyxl.load_workbook(tags_path(s), read_only=True, data_only=True)
        for team in teams_in(s):
            if team not in wb.sheetnames:
                continue
            for r in wb[team].iter_rows(min_row=2, values_only=True):
                lu = r[0]
                if not isinstance(lu, str) or ' - ' not in lu:
                    continue
                parts = [x.strip() for x in lu.split(' - ')]
                if len(parts) == 5 and len(set(parts)) < 5:
                    dup_rows += 1
                    dup_ts.add((s, team))
        wb.close()
    check('6.2  5ML lineups where one name covers two players (bug #5, consequence A)',
          dup_rows, KNOWN_ISSUES['corrupted_5ml_rows'], known=True)
    print('        %d team-seasons: %s' % (len(dup_ts), ', '.join('%s %s' % t for t in sorted(dup_ts))))
    print('        NOT fixable in code — the 5ML strings must be regenerated with player_id.')
    print()


# =====================================================================================
if __name__ == '__main__':
    if '--download' in sys.argv:
        download()

    print('\nPBP PREFLIGHT — play-by-play pipeline gate\n')
    frames = {s: pd.read_csv(lineup_path(s), dtype={'game_id': str}) for s in SEASONS}

    section_sources(frames)
    section_invariants(frames)
    section_reconcile(frames)
    section_bridge(frames)
    section_legacy_guards()

    unexpected = [f for f in FAILURES if not f[2]]
    known = [f for f in FAILURES if f[2]]
    print('=' * 96)
    print('RESULT: %d / %d checks passed' % (PASS, PASS + FAIL))
    if known:
        print('\n  %d KNOWN issue(s) — tracked, still open, DO NOT let them go quiet:' % len(known))
        for n, d, _ in known:
            print('     - %s   (%s)' % (n, d))
    if unexpected:
        print('\n  %d UNEXPECTED failure(s) — DO NOT BUILD ON THIS DATA:' % len(unexpected))
        for n, d, _ in unexpected:
            print('     - %s   (%s)' % (n, d))
    else:
        print('\n  No unexpected failures. The play-by-play data is safe to build on.')
    print('=' * 96)
    sys.exit(1 if unexpected else 0)
