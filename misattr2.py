"""Correct misattribution analysis, working from the WORKBOOK's own 5ML rows.

For each affected team-season, walk the workbook lineup rows. A row is CORRUPTED if its
5 name-strings collapse to <5 distinct strings (one name covers two players). For those
rows, compare:
  - workbook scenario (column 27, as the workbook assigned it)
  - correct scenario: the TRUE composition, recovered by matching the pbp stint(s) with the
    same clean players + the two real players behind the collapsed name.
Report minutes that were placed in the wrong bundle.
"""
import json, openpyxl
import pandas as pd
from collections import Counter, defaultdict
from continuity_lib import tags_path, load_tags, strip_team
from pbp_preflight import parse_lineup, initial_key, lineup_path, tag_key_forms

LOOKUP={tuple(map(int,k.split(','))):v for k,v in json.load(open('scenario_lookup.json')).items()}
BUNDLE={'Starters + Deep Bench Player':'PRESERVE','Short Bench Preserved':'PRESERVE',
        'Starters + Short Bench Player':'PILFER','Short Bench Pilfered':'PILFER',
        'Starter Baseline':'BASELINE','Garbage Time':'GARBAGE'}
HOU_FIX={'jalen green':'ST','jeff green':'SB'}

AFFECTED=[('2021-22','DEN'),('2022-23','OKC'),('2023-24','HOU'),('2023-24','OKC'),
          ('2024-25','HOU'),('2024-25','OKC'),('2025-26','GSW'),('2025-26','OKC')]

def true_comp_minutes(season, team, tg):
    """From pbp: for each stint, the true (ST,SB,DB,GT) comp and minutes, keyed by the
    frozenset of initial-keys on the floor (to match workbook rows) + how many share the dup."""
    df=pd.read_csv(lineup_path(season),dtype={'game_id':str}); df=df[df.team==team]
    out=defaultdict(lambda: defaultdict(float))  # ikey-multiset -> true_scenario -> minutes
    for r in df.itertuples():
        players=parse_lineup(r.lineup_team)
        ikeys=tuple(sorted(initial_key(n) for _,n in players))
        comp=Counter(); ok=True
        for pid,name in players:
            if (season,team)==('2023-24','HOU') and name.lower() in HOU_FIX:
                t=HOU_FIX[name.lower()]
            else:
                t=next((tg[f] for f in tag_key_forms(name) if f in tg),None)
            if t is None: ok=False;break
            comp[t]+=1
        if not ok: continue
        scen=LOOKUP.get((comp.get('ST',0),comp.get('SB',0),comp.get('DB',0),comp.get('GT',0)))
        out[ikeys][scen]+=r.secs_played/60
    return out

print('%-8s %-4s %10s %10s %8s   %s' % ('season','team','corruptMin','wrongBundle','%wrong','net shift (pres/pilf)'))
rows=[]
for season,team in AFFECTED:
    tags,_=load_tags(season); tg=tags.get(team,{})
    truemap=true_comp_minutes(season,team,tg)
    wb=openpyxl.load_workbook(tags_path(season),read_only=True,data_only=True)
    corrupt_min=0.0; wrong=defaultdict(float)
    for r in wb[team].iter_rows(min_row=2, values_only=True):
        lu=r[0]
        if not isinstance(lu,str) or ' - ' not in lu or len(r)<28: continue
        parts=[p.strip() for p in lu.split(' - ')]
        if len(set(parts))==5: continue      # not corrupted
        mn=r[2] if isinstance(r[2],(int,float)) else 0
        wb_scen=r[27]
        corrupt_min+=mn
        wb_bundle=BUNDLE.get(wb_scen,'?')
        # the true scenario(s) for this exact lineup: match on initial-keys
        ikeys=tuple(sorted(initial_key(strip_team(p,team)) for p in parts))
        tm=truemap.get(ikeys,{})
        if not tm:  # couldn't match; skip (rare)
            continue
        # distribute the workbook minutes across the true scenarios by their pbp proportion
        tot=sum(tm.values())
        for scen,m in tm.items():
            frac=m/tot
            tb=BUNDLE.get(scen,'?')
            if tb!=wb_bundle:
                wrong[(wb_bundle,tb)]+=mn*frac
    wb.close()
    wrongtot=sum(wrong.values())
    to_pres=sum(m for (a,b),m in wrong.items() if b=='PRESERVE')-sum(m for (a,b),m in wrong.items() if a=='PRESERVE')
    to_pilf=sum(m for (a,b),m in wrong.items() if b=='PILFER')-sum(m for (a,b),m in wrong.items() if a=='PILFER')
    rows.append((season,team,corrupt_min,wrongtot,wrong,to_pres,to_pilf))
    print('%-8s %-4s %10.0f %10.0f %7.1f%%   pres%+.0f pilf%+.0f' %
          (season,team,corrupt_min,wrongtot,100*wrongtot/corrupt_min if corrupt_min else 0,to_pres,to_pilf))

print('\n=== detailed bundle flows ===')
for season,team,cm,wt,wrong,tp,tpi in rows:
    if wt<1: continue
    print('%s %s:' % (season,team))
    for (a,b),m in sorted(wrong.items(),key=lambda x:-x[1]):
        if m>=1: print('   %-9s -> %-9s  %6.0f min' % (a,b,m))
