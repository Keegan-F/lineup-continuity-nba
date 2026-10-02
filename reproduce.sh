#!/usr/bin/env bash
# One-command reproduction of the headline results.
# Run from the repository root:  bash reproduce.sh
set -euo pipefail

echo "== 1/4  Python dependencies =="
python -m pip install -r requirements.txt

echo "== 2/4  Fetch play-by-play (public, not redistributed here) =="
python fetch_pbp.py

# Point the code at this repo's data layout (both scripts honour these env vars)
export CONTINUITY_DATA="$(pwd)/data/source"
export PBP_DATA="$(pwd)/pbp"

echo "== 3/4  Validate play-by-play against the box-score sources (77-check gate) =="
python code/pbp_preflight.py

echo "== 4/4  Reproduce headline + regression checks (63-check gate) =="
python code/verify_all.py

echo ""
echo "Done. Headline pooled NRG (~+1.6) and the 150 team-season results are reproduced above."
echo "To regenerate the figures:  python code/make_charts.py"
