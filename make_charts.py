"""
make_charts.py — Regenerate the core charts from the canonical data, in house style.

Run:  python3 make_charts.py            (writes PNGs to /mnt/user-data/outputs/)

Covers the main data charts. Each function is standalone — call individually if you only
need one. All read from continuity_lib (never from cached JSON), so they cannot go stale.
"""
import os
import numpy as np
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from continuity_lib import SEASONS, POSITIONS, extract_all_scenarios, by_position_pooled

# ---- house style ----
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Nimbus Roman', 'Liberation Serif', 'Times New Roman', 'DejaVu Serif']
NAVY, TEAL, ORNG, GREEN, GRAY = '#1f3864', '#1f6f8c', '#e07e2c', '#3a7d44', '#8a8a8a'
OUT = os.environ.get('CONTINUITY_OUT', '/mnt/user-data/outputs/')
os.makedirs(OUT, exist_ok=True)


def _despine(ax, keep=('left', 'bottom')):
    for sp in ax.spines:
        ax.spines[sp].set_visible(sp in keep)
    ax.tick_params(length=0)


def chart_season_gap(D):
    """Per-season NRG bars."""
    vals = [np.mean([r['L'] for r in D if r['s'] == s]) for s in SEASONS]
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    ax.bar(range(5), vals, color=TEAL, width=0.6, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.06, '+%.1f' % v, ha='center', fontsize=12, fontweight='bold', color=NAVY)
    ax.axhline(0, color='black', lw=1.1)
    ax.set_xticks(range(5)); ax.set_xticklabels(SEASONS, fontsize=11)
    ax.set_ylabel('Net Ratings Gap', fontsize=12); ax.set_ylim(0, max(vals) + 0.7)
    ax.set_title('Net Ratings Gap by Season\n2021-22 to 2025-26', fontsize=15, fontweight='bold', pad=12)
    ax.grid(axis='y', color='#ccc', lw=0.7, zorder=0); _despine(ax)
    plt.tight_layout(); plt.savefig(OUT + 'SeasonGap_5season.png', dpi=150, bbox_inches='tight'); plt.close()
    print('SeasonGap_5season.png', [round(v, 2) for v in vals])


def chart_decomposition(D):
    """Finding 3.3 (JFF numbering): net rating by level, preserve vs pilfer, with
    minute-distribution labels. y-axis fixed at (-4, 6) per Keegan."""
    def wm(rows, key):
        num = sum((r[key + '_net'] or 0) * (r[key + '_min'] or 0) for r in rows if r[key + '_net'] is not None)
        den = sum((r[key + '_min'] or 0) for r in rows if r[key + '_net'] is not None)
        return num / den if den else 0.0

    lv = {'base': [], 'st_deep': [], 'st_short': [], 'prsv': [], 'pilf': []}
    for s in SEASONS:
        rows = [r for r in D if r['s'] == s]
        for k in lv:
            lv[k].append(wm(rows, k))
    base = float(np.mean(lv['base']))
    pres = [base, float(np.mean(lv['st_deep'])), float(np.mean(lv['prsv']))]
    pilf = [base, float(np.mean(lv['st_short'])), float(np.mean(lv['pilf']))]
    tot_p = float(np.mean([r['E'] for r in D])); tot_f = float(np.mean([r['I'] for r in D]))
    pres.append(tot_p); pilf.append(tot_f)
    cats = ['Starter Baseline', 'Starter + 1 Bench', 'Bench', 'Total']

    x = np.arange(4); w = 0.34
    fig, ax = plt.subplots(figsize=(10.1, 6.4))
    b1 = ax.bar(x - w / 2, pres, w, color=TEAL, zorder=3)
    b2 = ax.bar(x + w / 2, pilf, w, color=ORNG, zorder=3)
    for xs, vs in ((x - w / 2, pres), (x + w / 2, pilf)):
        for xi, v in zip(xs, vs):
            inside = abs(v) > 0.55
            ax.text(xi, v - 0.18 if (v > 0 and inside) else (v + 0.08 if v > 0 else v - 0.30),
                    '%.1f' % v, ha='center', va='top' if (v > 0 and inside) else 'bottom',
                    fontsize=11, color='white' if inside else (TEAL if v > 0 else ORNG),
                    fontweight='bold' if not inside else 'normal', zorder=5)
    # gap callouts
    for i in (1, 2, 3):
        g = pres[i] - pilf[i]
        top = max(pres[i], pilf[i]); bot = min(pres[i], pilf[i])
        xb = x[i] + w / 2 + 0.30
        ax.plot([xb, xb], [bot, top], color='#555', lw=1.2, zorder=4)
        ax.annotate('Net Ratings\nGap: %+.1f' % g, xy=(xb, top), xytext=(xb, 5.4),
                    ha='center', fontsize=9.5,
                    bbox=dict(boxstyle='round,pad=0.32', fc='#e8e8e8', ec='#999', lw=0.7), zorder=6)
    ax.axhline(0, color='black', lw=1.3, zorder=2)
    ax.set_ylim(-4, 6); ax.set_xlim(-0.6, 4.3)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=11.5)
    ax.set_ylabel('Net Ratings', fontsize=12)
    # minute distribution under the two flexible levels
    ax.text(1, -0.075, '20% of 5ML minutes', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=9, color='#555', style='italic')
    ax.text(2, -0.075, '62% of 5ML minutes', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=9, color='#555', style='italic')
    ax.grid(axis='y', color='#ccc', lw=0.8, zorder=0); _despine(ax, keep=('bottom',))
    ax.set_title('Average Net Ratings by Bench Strategy\n2021-22 to 2025-26',
                 fontsize=16, fontweight='bold', pad=14)
    ax.legend(handles=[b1, b2], labels=['Preserve Short Bench', 'Pilfer Short Bench'],
              loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False, fontsize=11.5)
    plt.tight_layout(); plt.savefig(OUT + 'BenchStrategy_bars_5season.png', dpi=150, bbox_inches='tight'); plt.close()
    print('BenchStrategy_bars_5season.png  gaps: 4S+1 %+.1f | Bench %+.1f | Total %+.1f'
          % (pres[1] - pilf[1], pres[2] - pilf[2], pres[3] - pilf[3]))


def chart_team_2526(D):
    """2025-26 NRG by team, sorted. Outliers clamped to the axis, true value in the label."""
    g = {r['t']: r['L'] for r in D if r['s'] == '2025-26'}
    teams = sorted(g, key=lambda t: -g[t]); CLAMP = 14.6
    fig, ax = plt.subplots(figsize=(9.6, 7.4))
    for i, t in enumerate(teams):
        v = g[t]; vc = max(-CLAMP, min(CLAMP, v)); c = TEAL if v >= 0 else ORNG
        ax.barh(i, vc, color=c, height=0.66, zorder=3)
        ax.text(vc + (0.25 if v >= 0 else -0.25), i, '%.1f' % v, va='center',
                ha='left' if v >= 0 else 'right', color=c, fontsize=9)
    ax.axvline(0, color='#888', lw=1.0)
    ax.set_xlim(-15, 15); ax.set_ylim(-0.8, len(teams) - 0.2); ax.invert_yaxis()
    ax.set_yticks(range(len(teams))); ax.set_yticklabels(teams, fontsize=8.5)
    ax.grid(axis='x', color='#ccc', lw=0.8, zorder=0); _despine(ax, keep=())
    ax.text(0.28, -0.07, 'Pilfer favored', transform=ax.transAxes, ha='center', fontsize=11.5)
    ax.text(0.72, -0.07, 'Preserve favored', transform=ax.transAxes, ha='center', fontsize=11.5)
    over = [t for t in teams if abs(g[t]) > CLAMP]
    if over:
        ax.text(0.5, -0.115, '%s extend beyond the axis and are clamped to the edge.'
                % ' and '.join('%s (%+.1f)' % (t, g[t]) for t in over),
                transform=ax.transAxes, ha='center', fontsize=8, color='#777', style='italic')
    ax.set_title('Net Ratings Gap by Team\n2025-26 Season', fontsize=16, fontweight='bold', pad=14)
    plt.tight_layout(); plt.savefig(OUT + 'TeamGap_2526.png', dpi=150, bbox_inches='tight'); plt.close()
    print('TeamGap_2526.png  top %s %+.1f | bottom %s %+.1f' % (teams[0], g[teams[0]], teams[-1], g[teams[-1]]))


def chart_smallmultiples(D):
    """Finding 3.5/3.7: 30 panels, one per team. 28 of 30 cross zero."""
    M = defaultdict(dict)
    for r in D:
        M[r['t']][r['s']] = r['L']
    teams = sorted(M); YL = 10
    fig, axes = plt.subplots(6, 5, figsize=(7.5, 9.0), sharex=True, sharey=True)
    for k, t in enumerate(teams):
        ax = axes[k // 5][k % 5]
        v = np.array([M[t][s] for s in SEASONS]); vc = np.clip(v, -YL, YL); xx = np.arange(5)
        ax.fill_between(xx, vc, 0, where=(vc >= 0), interpolate=True, color=TEAL, alpha=0.55, zorder=2)
        ax.fill_between(xx, vc, 0, where=(vc <= 0), interpolate=True, color=ORNG, alpha=0.60, zorder=2)
        ax.plot(xx, vc, color='#333', lw=1.3, zorder=3)
        ax.scatter(xx, vc, s=11, color='#333', zorder=4)
        ax.axhline(0, color='#555', lw=0.9, zorder=1)
        ax.set_xlim(-0.4, 4.4); ax.set_ylim(-YL, YL)
        ax.set_title(t, fontsize=11, fontweight='bold', color=NAVY, pad=3)
        ax.set_xticks(range(5)); ax.set_yticks([-10, 0, 10])
        ax.set_xticklabels(['22', '23', '24', '25', '26'] if k // 5 == 5 else [], fontsize=8)
        ax.set_yticklabels(['-10', '0', '+10'] if k % 5 == 0 else [], fontsize=7.5)
        _despine(ax)
    fig.suptitle('Net Ratings Gap by Team, Season by Season\n'
                 'teal = preserve-favored   \u2022   orange = pilfer-favored',
                 fontsize=15, fontweight='bold', y=0.998)
    fig.text(0.5, 0.006, '28 of the 30 teams cross zero at least once; only Denver and the '
             'Lakers stayed preserve-favored in all five seasons.',
             ha='center', fontsize=9.5, color='#555', style='italic')
    plt.tight_layout(rect=[0, 0.02, 1, 0.965]); plt.subplots_adjust(hspace=0.42, wspace=0.18)
    plt.savefig(OUT + 'Finding37_smallmultiples.png', dpi=150, bbox_inches='tight'); plt.close()
    print('Finding37_smallmultiples.png')


def chart_forest(D):
    """Per-season + pooled estimate with franchise-clustered CI."""
    L = np.array([r['L'] for r in D])
    bt = defaultdict(list)
    for r in D:
        bt[r['t']].append(r['L'])
    tm = np.array([np.mean(v) for v in bt.values()])
    mean = L.mean(); se = tm.std(ddof=1) / np.sqrt(len(tm))
    lo, hi = mean - 1.96 * se, mean + 1.96 * se
    per = [(s, np.mean([r['L'] for r in D if r['s'] == s])) for s in SEASONS]
    labels = [s for s, _ in per] + ['Pooled (5-season,\nfranchise-clustered)']
    vals = [v for _, v in per] + [mean]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for i, (lab, v) in enumerate(zip(labels, vals)):
        y = len(labels) - 1 - i
        if 'Pooled' in lab:
            ax.plot([lo, hi], [y, y], color=NAVY, lw=2.4, zorder=3)
            ax.plot(v, y, 'D', color=NAVY, ms=10, zorder=4)
            ax.text(hi + 0.15, y, '%.2f [%.2f, %.2f]' % (v, lo, hi), va='center',
                    fontsize=10, color=NAVY, fontweight='bold')
        else:
            ax.plot(v, y, 'o', color=TEAL, ms=8, zorder=4)
            ax.text(v + 0.15, y, '%+.2f' % v, va='center', fontsize=9.5, color='#333')
    ax.axvline(0, color='#999', ls='--', lw=1)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels[::-1], fontsize=10)
    ax.set_xlim(-1, 3.2); ax.set_xlabel('Net Ratings Gap (Preserve \u2212 Pilfer)', fontsize=11)
    _despine(ax, keep=('bottom',))
    ax.set_title('Net Ratings Gap: Per-Season and Pooled Estimates', fontsize=14, fontweight='bold', pad=10)
    plt.tight_layout(); plt.savefig(OUT + 'Continuity_forest_plot.png', dpi=150, bbox_inches='tight'); plt.close()
    print('Continuity_forest_plot.png  pooled %.2f [%.2f, %.2f]' % (mean, lo, hi))


def chart_by_position(min_deep_minutes=0):
    """Finding 3.9, WITH the deep-bench-replacement rule.

    NOTE: this is the chart that is NOT yet in the paper. The published version still
    shows the pre-fix, pre-rule values (+3.5/+4.0/+3.4/+4.2/+4.2).
    """
    league, kept = by_position_pooled(apply_rule=True, min_deep_minutes=min_deep_minutes)
    gaps = [league[p] for p in POSITIONS]
    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    ax.bar(range(5), gaps, color=TEAL, width=0.6, zorder=3)
    for i, g in enumerate(gaps):
        ax.text(i, g + 0.06, '+%.1f' % g, ha='center', fontsize=12, fontweight='bold', color=NAVY)
    ax.axhline(0, color='black', lw=1.1, zorder=2)
    ax.set_xticks(range(5))
    ax.set_xticklabels(['Point Guard', 'Shooting Guard', 'Small Forward', 'Power Forward', 'Center'],
                       fontsize=10.5)
    ax.set_ylabel('Net Ratings Gap (Preserve \u2212 Pilfer)', fontsize=11.5)
    ax.set_ylim(0, max(gaps) + 0.9)
    ax.set_title('Net Ratings Gap by Starter Position\n2021-22 to 2025-26',
                 fontsize=15, fontweight='bold', pad=10)
    ax.text(0.5, -0.17, 'Team-positions whose starter was never replaced by a Deep Bench player '
            'are excluded as not calculable.', transform=ax.transAxes, ha='center',
            fontsize=8.4, color='#666', style='italic')
    ax.grid(axis='y', color='#ccc', lw=0.7, zorder=0); _despine(ax, keep=('bottom',))
    plt.tight_layout(); plt.savefig(OUT + 'GapByPosition_5season.png', dpi=150, bbox_inches='tight'); plt.close()
    print('GapByPosition_5season.png', {p: round(league[p], 1) for p in POSITIONS}, 'kept', kept)


if __name__ == '__main__':
    D = [r for r in extract_all_scenarios() if r['L'] is not None]
    print('loaded %d team-seasons\n' % len(D))
    chart_season_gap(D)
    chart_decomposition(D)
    chart_team_2526(D)
    chart_smallmultiples(D)
    chart_forest(D)
    chart_by_position()
    print('\ndone')
