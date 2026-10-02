# Bug #5 — Impact on the 8 Affected Team-Seasons

Scope: the 8 team-seasons whose 5ML lineup strings collapse two distinct players into one
name (376 rows, 2,144 minutes). This is code-and-data analysis only; the paper is untouched.

---

## What I could establish with certainty, and what I could not

Two things about bug #5 are **cleanly knowable** and I report them below:

1. **Where the corrupted minutes actually belong.** Once the play-by-play resolves the two
   hidden players by `player_id`, the correct scenario for each stint is a *deterministic*
   lookup on the lineup's (Starter, Short-Bench, Deep-Bench, Garbage-Time) composition. I
   verified that lookup reproduces the workbook's own scenario label on **81,311 of 81,311
   clean lineups — 100.0%**. So the corrected classification is not a model; it is exact.

2. **A bound on the distortion**, computed entirely on the workbook's own net ratings
   (published NRG vs. NRG with the corrupted rows dropped). Because both sides use the
   workbook's numbers, this has **no estimator confound**.

One thing is **not cleanly knowable from the workbook**, and I want to be explicit rather
than paper over it: a **single corrected NRG per team-season**. A corrupted workbook row is
one aggregate (one minutes value, one net rating) that actually spans *several* true
five-man compositions — e.g. OKC 2022-23's `... Jay.Williams - Jay.Williams` is sometimes
both Williamses on the floor (4S+1DB, Preserve) and sometimes only one (a different
scenario). You cannot re-split one aggregate net rating into its true pieces without going
to the play-by-play for the pieces' net ratings — and that reintroduces the ~0.3-1.0-point
estimator gap between play-by-play and NBA.com net ratings that rung 1 already measured.

I tried three ways to net that gap back out. All three produced unstable per-team numbers
(the clean-row estimator gap is itself noisy on a single small team-season and does not
transfer reliably to the corrupted rows). **So I am declining to report a single "corrected
NRG."** Reporting one would be presenting an estimator artifact as a bug fix — exactly the
kind of false precision we just spent the last analysis stripping out of the paper.

---

## The bound: how much the corrupted rows move each team-season

Workbook net ratings throughout; "drop-corrupt" = published NRG recomputed with the
corrupted rows removed. The shift is a **lower bound in magnitude** on the true correction
(dropping understates it, because the corrupted minutes should be *re-assigned*, not
deleted — but the re-assignment can only add to the moved mass).

| season | team | published | drop corrupt | shift | corrupt min |
|---|---|---:|---:|---:|---:|
| 2021-22 | DEN | +3.00 | +6.10 | **+3.10** | 198 |
| 2022-23 | OKC | −3.60 | −5.26 | **−1.66** | 655 |
| 2023-24 | HOU | +1.59 | −0.16 | **−1.74** | 620 |
| 2023-24 | OKC | −6.79 | −9.38 | **−2.59** | 247 |
| 2024-25 | HOU | −4.10 | −4.93 | −0.82 | 156 |
| 2024-25 | OKC | +1.32 | +2.30 | +0.98 | 172 |
| 2025-26 | GSW | −0.94 | −0.43 | +0.51 | 17 |
| 2025-26 | OKC | +4.59 | +3.46 | −1.12 | 79 |

**These are large.** Five of eight move by more than a full net-rating point; DEN moves
+3.1, OKC 2023-24 moves −2.6, HOU 2023-24 flips sign. Against a pooled effect of +1.6, a
per-team distortion of 1-3 points is the difference between a real finding and noise. This
is why the named-team claims (POR-best, the Denver instability claim) were fragile: several
of the teams involved are on this list.

**Pooled, it barely registers:** 2,144 of 593,709 minutes is 0.36%, and dropping them moves
the headline +1.597 → +1.575 (−0.022). Bug #5 is a *team-level* defect, not a pooled one.

---

## Where the corrupted minutes truly belong (certain — pure classification)

From play-by-play, resolving both players by ID, here is the corrected scenario for the
collapsed minutes in each of the **7 fixable** team-seasons (full detail in
`bug5_corrected_flow.json`):

- **2022-23 OKC** — 288 min move into **4S+1DB (Preserve)**. This is the SGA-Dort-Giddey-
  Jalen-Jaylin lineup the workbook had labeled *Short Bench Pilfered*. The single largest
  and cleanest misclassification.
- **2021-22 DEN** — 198 min split across Pilfered / 4S+1SB / Preserved (Jeff Green ST vs
  JaMychal Green SB).
- **2023-24 OKC**, **2024-25 OKC**, **2025-26 OKC** — Jalen Williams (ST) vs Jaylin
  Williams (SB/DB); minutes redistribute across the bench and 4S+1 scenarios.
- **2024-25 HOU** — Jalen Green (ST) vs Jeff Green (DB); 51 min move into 4S+1DB.
- **2025-26 GSW** — Stephen Curry (ST) vs Seth Curry (DB); only 17 min, negligible.

---

## The 8th team-season: HOU 2023-24 is NOT fixable by re-keying

Both Greens are tagged **GT, GP/GS = (0,0)** in the roster-tag list. Jalen Green started ~76
games. The **tags themselves are wrong**, not just the lineup key — so resolving player IDs
correctly attributes the *minutes* but still sends both players to Garbage Time. Re-keying
cannot fix a broken tag.

**HOU 2023-24 needs its roster tags re-derived at source** before any lineup fix is
meaningful. Concretely: Jalen Green should be **ST** (82-ish GP, ~76 GS), Jeff Green a
bench tag. Until then, that team-season's every number is unreliable and should be treated
as such.

---

## Deliverables produced

- `scenario_lookup.json` — the (ST,SB,DB,GT) → scenario rule, verified 100% against the
  workbook. Reusable, and worth adding to `verify_all.py` as a guard.
- `bug5_corrected_flow.json` — the corrected scenario assignment of every collapsed minute,
  for the 7 fixable team-seasons.
- `player_id_bridge.json` (from the preflight) — the id→tag-key spine the real fix needs.

## Recommended path to a genuine fix (not done here — awaiting your direction)

The corrupted rows can only be correctly repaired by **rebuilding those 8 team-seasons'
5ML aggregates from the play-by-play, keyed on player_id**, and re-deriving HOU 2023-24's
tags by hand. That makes the whole team-season play-by-play-native, which means it should
then be compared to the *other* 142 on the same (play-by-play) footing — i.e. it argues for
the play-by-play estimator swap we discussed as rung 1, at least for these 8. I did not do
this because it changes the estimator for a subset, and that is a decision about the
paper's methodology, not a bug fix — your call.
