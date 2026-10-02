# Finding 3.9 — drop-in text

Replaces the current 3.9 section. The published chart shows the pre-fix values
(+3.5 / +4.0 / +3.4 / +4.2 / +4.2) and must be swapped for
`GapByPosition_5season.png`.

---

## Corrected values (pooled, 5 seasons)

| PG | SG | SF | PF | C |
|---|---|---|---|---|
| **+3.3** | **+3.1** | **+3.1** | **+3.9** | **+3.7** |

Retained team-seasons: PG 109 · SG 98 · SF 96 · PF 99 · C 116.

---

## Methodology note (place directly beneath the chart)

> A position is calculable for a team-season only if that position's starter recorded
> minutes in a *Starters + Deep Bench Player* (4S+1DB) lineup — that is, only if he was
> in fact replaced by a Deep Bench player at some point in the season. Where he was not,
> his Short-Bench-Preserved minutes are excluded and the team-season drops out of that
> position's league average. This prevents preserve-side minutes from being credited to a
> position that was never actually exposed to a continuity decision. Team-position
> observations retained: PG 109, SG 98, SF 96, PF 99, C 116 of 150.

---

## Robustness paragraph (appendix, with `GapByPosition_Robustness_5season.png`)

> The Deep-Bench-replacement rule qualifies a position on any non-zero 4S+1DB minutes.
> Because a small number of team-positions qualify on very few minutes, we re-estimate
> the by-position gap under progressively stricter minute floors. The level of the
> finding is insensitive to this choice: every position remains positive under every
> floor through 50 minutes, within a band of roughly +1.9 to +4.7. The *ordering* is not.
> The leading position changes at nearly every cut point — Power Forward at the specified
> rule, Small Forward at a 5-minute floor, Center at 10, Point Guard from 20 minutes
> onward — and at a 10-minute floor all five positions fall within 0.19 net rating points
> of one another. Beyond a 50-minute floor the pooled sample falls below 170 team-positions
> and estimates become unstable (Power Forward turns negative on 13 observations), which we
> read as small-sample noise rather than signal. We therefore retain the rule as specified
> and report the by-position gaps as evidence that the continuity premium holds at all five
> positions, while declining to interpret the ranking among them.

---

## Why the rule stays at `> 0`

Not because the marginal cases are individually defensible — LAC 2024-25 SG qualifies on a
single minute (net +100.0) and thereby admits a 767-minute preserve bundle — but because
the sweep shows they are immaterial. Excluding them (a 5-minute floor) moves PG from +3.35
to +2.96 and leaves every qualitative claim intact. Raising the floor does not sharpen the
estimate; it trades sample for a different, equally arbitrary cut. Holding at `> 0` keeps
maximum n, preserves the rule as originally specified, and avoids a threshold a referee
could fairly call chosen after seeing the results.

---

## Checklist for the JFF revision

- [ ] Swap chart → `GapByPosition_5season.png` (match by PNG dimensions, not `imageN`)
- [ ] Replace the five values in body text: +3.5/+4.0/+3.4/+4.2/+4.2 → **+3.3/+3.1/+3.1/+3.9/+3.7**
- [ ] Update the per-season 3.9 table (all 25 cells) if it appears in the body
- [ ] Insert methodology note beneath the chart
- [ ] Add robustness paragraph + `GapByPosition_Robustness_5season.png` to the appendix
- [ ] Confirm the "band is tight / ordering tentative" caveat now points at the robustness exhibit
- [ ] Re-run `verify_all.py` (63/63) after any pipeline touch
