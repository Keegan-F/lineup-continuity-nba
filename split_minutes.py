"""For each of the 8 collisions, the workbook treated two players as ONE name. From the
play-by-play (player_id), compute how the on-court minutes under that shared name actually
divide between the two real players -- overall, and as starters."""
import pandas as pd
from collections import defaultdict
from pbp_preflight import parse_lineup, initial_key, lineup_path

COLLISIONS = [
 ('2021-22','DEN','J.GREEN'),
 ('2022-23','OKC','J.WILLIAMS'),
 ('2023-24','HOU','J.GREEN'),
 ('2023-24','OKC','J.WILLIAMS'),
 ('2024-25','HOU','J.GREEN'),
 ('2024-25','OKC','J.WILLIAMS'),
 ('2025-26','GSW','S.CURRY'),
 ('2025-26','OKC','J.WILLIAMS'),
]

for season, team, sharedkey in COLLISIONS:
    df = pd.read_csv(lineup_path(season), dtype={'game_id':str}); df=df[df.team==team]
    mins=defaultdict(float); names={}; gp=defaultdict(set); gs=defaultdict(int)
    start_min=defaultdict(float)
    for r in df.itertuples():
        # is this a starting stint? period 1 stint 1
        starter_stint = (r.period==1 and r.stint==1)
        for pid,name in parse_lineup(r.lineup_team):
            if initial_key(name)==sharedkey:
                names[pid]=name
                mins[pid]+=r.secs_played/60
                gp[pid].add(r.game_id)
                if starter_stint: start_min[pid]+=r.secs_played/60
    # also count games started
    for gid,g in df.groupby('game_id'):
        p1=g[(g.period==1)&(g.stint==1)]
        if len(p1):
            for pid,name in parse_lineup(p1.iloc[0].lineup_team):
                if initial_key(name)==sharedkey: gs[pid]+=1
    tot=sum(mins.values())
    print('=== %s %s  shared name "%s"  (total %.0f min under this name) ===' % (season,team,sharedkey,tot))
    for pid in sorted(mins, key=lambda p:-mins[p]):
        print('   %-18s id=%-8d GP=%2d GS=%2d   %6.0f min  = %5.1f%% of shared minutes'
              % (names[pid], pid, len(gp[pid]), gs[pid], mins[pid], 100*mins[pid]/tot))
    print()
