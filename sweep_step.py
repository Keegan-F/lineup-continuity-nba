"""Resumable min_deep_minutes sweep. Usage: python3 sweep_step.py 0 5
Appends to sweep_results.json so it survives container resets."""
import sys, json, os
from continuity_lib import by_position_pooled, POSITIONS
F = 'sweep_results.json'
res = json.load(open(F)) if os.path.exists(F) else {}
for thr in [int(a) for a in sys.argv[1:]]:
    if str(thr) in res:
        print('thr=%d cached' % thr); continue
    lg, kept = by_position_pooled(apply_rule=True, min_deep_minutes=thr)
    res[str(thr)] = {'vals': {p: lg[p] for p in POSITIONS},
                     'kept': {p: kept[p] for p in POSITIONS}}
    json.dump(res, open(F, 'w'))
    print('thr=%-4d' % thr, {p: round(lg[p], 2) for p in POSITIONS},
          'n=%d' % sum(kept[p] for p in POSITIONS), flush=True)
print('have thresholds:', sorted(int(k) for k in res))
