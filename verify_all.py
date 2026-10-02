"""
verify_all.py — Regression test. Recomputes every headline number in the paper from the
canonical files and checks it against the published value.

Run:  python3 verify_all.py
If any line prints FAIL, the pipeline has drifted from the paper. Investigate before
trusting any new output.
"""
import numpy as np
from collections import defaultdict

from continuity_lib import (SEASONS, POSITIONS, preflight, extract_all_scenarios,
                            load_tags, games_with_non_starters,
                            by_position_pooled, by_position)

EXPECTED = {
    'headline_nrg': 1.60,
    'ci_low': 0.71, 'ci_high': 2.48,
    'per_season': [1.6, 1.1, 2.2, 0.5, 2.7],
    'preserve_mean': 1.3, 'pilfer_mean': -0.3,
    'preserve_sd': 6.3, 'pilfer_sd': 5.5,
    'baseline': 4.9, 'st_deep': -1.4, 'st_short': 3.0, 'prsv': 2.3, 'pilf': -2.3,
    'gap_4s1': -4.6, 'gap_bench': 4.6,
    'tags_2526': (177, 196, 180, 108),
    'top_team': ('POR', 5.9), 'bottom_team': ('IND', -3.9),
    'top_2526': ('POR', 17.1), 'bottom_2526': ('MIA', -6.1),
    'teams_crossing_zero': 28,
    'majority_preserve_team_seasons': 19,
    # bug #5 fix (full-name -> tag-key resolution): SG and PF move; kept counts 109/99/96/100/116
    'bypos_pooled': {'PG': 3.3, 'SG': 3.0, 'SF': 3.1, 'PF': 4.0, 'C': 3.7},
    'bypos_per_season': {
        '2021-22': {'PG': 2.8, 'SG': 3.5, 'SF': 4.7, 'PF': 5.2, 'C': 3.8},
        '2022-23': {'PG': 3.7, 'SG': 4.2, 'SF': 1.5, 'PF': 4.1, 'C': 2.6},
        '2023-24': {'PG': 2.8, 'SG': 0.6, 'SF': 2.8, 'PF': 2.9, 'C': 4.6},
        '2024-25': {'PG': 2.8, 'SG': 1.7, 'SF': 1.7, 'PF': 3.1, 'C': 3.0},
        '2025-26': {'PG': 4.7, 'SG': 5.0, 'SF': 4.6, 'PF': 4.2, 'C': 4.6},
    },
    'okc_2223_nonstarter_games': 82,   # 4 tagged Starters -> must be all 82
    'lac_2425_nonstarter_games': 35,
}

results = []

# Fail fast and loudly if the source workbooks aren't present.
preflight()
print()


def check(label, got, want, tol=0.06):
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) else got == want
    results.append(ok)
    print('%-46s got %-16s want %-16s %s'
          % (label, round(got, 2) if isinstance(got, float) else got,
             want, 'OK' if ok else '*** FAIL ***'))


print('=' * 96)
print('CORE NRG')
print('=' * 96)
D = [r for r in extract_all_scenarios() if r['L'] is not None]
check('team-seasons', len(D), 150)

L = np.array([r['L'] for r in D])
check('headline NRG', L.mean(), EXPECTED['headline_nrg'])

by_team = defaultdict(list)
for r in D:
    by_team[r['t']].append(r['L'])
team_means = np.array([np.mean(v) for v in by_team.values()])
se = team_means.std(ddof=1) / np.sqrt(len(team_means))
check('CI low  (franchise-clustered)', L.mean() - 1.96 * se, EXPECTED['ci_low'])
check('CI high (franchise-clustered)', L.mean() + 1.96 * se, EXPECTED['ci_high'])

for i, s in enumerate(SEASONS):
    vals = [r['L'] for r in D if r['s'] == s]
    check('per-season NRG %s' % s, np.mean(vals), EXPECTED['per_season'][i])

E = np.array([r['E'] for r in D])
I = np.array([r['I'] for r in D])
check('preserve mean', E.mean(), EXPECTED['preserve_mean'])
check('pilfer mean', I.mean(), EXPECTED['pilfer_mean'])
check('preserve SD', E.std(ddof=1), EXPECTED['preserve_sd'])
check('pilfer SD', I.std(ddof=1), EXPECTED['pilfer_sd'])

print()
print('=' * 96)
print('DECOMPOSITION (minute-weighted, 5-season)')
print('=' * 96)


def wmean(key):
    num = sum((r[key + '_net'] or 0) * (r[key + '_min'] or 0) for r in D if r[key + '_net'] is not None)
    den = sum((r[key + '_min'] or 0) for r in D if r[key + '_net'] is not None)
    return num / den if den else 0.0


base, sdeep, sshort = wmean('base'), wmean('st_deep'), wmean('st_short')
prsv, pilf = wmean('prsv'), wmean('pilf')
check('Starter Baseline', base, EXPECTED['baseline'])
check('4S+1 Deep Bench (preserve)', sdeep, EXPECTED['st_deep'])
check('4S+1 Short Bench (pilfer)', sshort, EXPECTED['st_short'])
check('Bench Preserved', prsv, EXPECTED['prsv'])
check('Bench Pilfered', pilf, EXPECTED['pilf'])

# The paper's Finding 3.2/3.3 chart computes each season's minute-weighted level, then
# averages the five seasons (NOT a single pooled minute-weighting). Gaps must match that.
def season_wmean(rows, key):
    num = sum((r[key + '_net'] or 0) * (r[key + '_min'] or 0) for r in rows if r[key + '_net'] is not None)
    den = sum((r[key + '_min'] or 0) for r in rows if r[key + '_net'] is not None)
    return num / den if den else 0.0


gaps_4s1, gaps_bench = [], []
for s in SEASONS:
    rows = [r for r in D if r['s'] == s]
    gaps_4s1.append(season_wmean(rows, 'st_deep') - season_wmean(rows, 'st_short'))
    gaps_bench.append(season_wmean(rows, 'prsv') - season_wmean(rows, 'pilf'))
check('gap @ 4S+1 level (chart method)', float(np.mean(gaps_4s1)), EXPECTED['gap_4s1'], tol=0.1)
check('gap @ Bench level (chart method)', float(np.mean(gaps_bench)), EXPECTED['gap_bench'], tol=0.1)

print()
print('=' * 96)
print('TEAMS / TAGS')
print('=' * 96)
avg = {t: np.mean(v) for t, v in by_team.items()}
top = max(avg, key=avg.get)
bot = min(avg, key=avg.get)
check('top team (5yr avg)', top, EXPECTED['top_team'][0])
check('top team value', avg[top], EXPECTED['top_team'][1])
check('bottom team (5yr avg)', bot, EXPECTED['bottom_team'][0])
check('bottom team value', avg[bot], EXPECTED['bottom_team'][1])

g26 = {r['t']: r['L'] for r in D if r['s'] == '2025-26'}
check('2025-26 top team', max(g26, key=g26.get), EXPECTED['top_2526'][0])
check('2025-26 top value', g26[max(g26, key=g26.get)], EXPECTED['top_2526'][1], tol=0.15)
check('2025-26 bottom team', min(g26, key=g26.get), EXPECTED['bottom_2526'][0])
check('2025-26 bottom value', g26[min(g26, key=g26.get)], EXPECTED['bottom_2526'][1], tol=0.15)

per_team_season = defaultdict(dict)
for r in D:
    per_team_season[r['t']][r['s']] = r['L']
crossing = sum(1 for t in per_team_season
               if not (all(v > 0 for v in per_team_season[t].values())
                       or all(v < 0 for v in per_team_season[t].values())))
check('teams crossing zero (Finding 3.5/3.7)', crossing, EXPECTED['teams_crossing_zero'])

majority = sum(1 for r in D if (r['B'] / (r['B'] + r['F'])) > 0.5)
check('team-seasons preserving majority', majority, EXPECTED['majority_preserve_team_seasons'])

tags26, _ = load_tags('2025-26')
counts = defaultdict(int)
for team in tags26:
    for _, tag in tags26[team].items():
        counts[tag] += 1
got_tags = (counts['ST'], counts['SB'], counts['DB'], counts['GT'])
check('2025-26 tag counts ST/SB/DB/GT', got_tags, EXPECTED['tags_2526'])

print()
print('=' * 96)
print('GRID / NON-STARTER COUNTS (distinct-Starter matching)')
print('=' * 96)
t22, _ = load_tags('2022-23')
_, okc = games_with_non_starters('2022-23', 'OKC', t22['OKC'])
check('OKC 2022-23 games w/ non-Starter', okc, EXPECTED['okc_2223_nonstarter_games'])

t24, _ = load_tags('2024-25')
_, lac = games_with_non_starters('2024-25', 'LAC', t24['LAC'])
check('LAC 2024-25 games w/ non-Starter', lac, EXPECTED['lac_2425_nonstarter_games'])

print()
print('=' * 96)
print('FINDING 3.9 — BY POSITION (new rule: requires 4S+1DB minutes)')
print('=' * 96)
pooled, kept = by_position_pooled(apply_rule=True)
for p in POSITIONS:
    check('pooled 5-season %s' % p, pooled[p], EXPECTED['bypos_pooled'][p], tol=0.08)
print('   kept team-seasons per position:', {p: kept[p] for p in POSITIONS})

print()
for s in SEASONS:
    league, _, k = by_position(s, apply_rule=True)
    for p in POSITIONS:
        check('%s %s' % (s, p), league[p], EXPECTED['bypos_per_season'][s][p], tol=0.08)
    print('   %s kept: %s' % (s, {p: k.get(p, 0) for p in POSITIONS}))

print()
print('=' * 96)
print('RESULT: %d / %d checks passed' % (sum(results), len(results)))
print('=' * 96)
