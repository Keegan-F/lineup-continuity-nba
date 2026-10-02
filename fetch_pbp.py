#!/usr/bin/env python3
"""Download the stint-level play-by-play this project depends on, from the public
ramirobentes/nba_pbp_data repository, into ./pbp/ as lineup_{2022..2026}.csv
(season label = end-year). This data is NOT redistributed in this repo; it is fetched
from its original public source on demand.

Usage:  python fetch_pbp.py
If the file layout upstream has changed, see https://github.com/ramirobentes/nba_pbp_data
and place the five lineup-final CSVs in ./pbp/ named lineup_2022.csv ... lineup_2026.csv.
"""
import os, sys, urllib.request

# end-year -> season folder label used upstream (edit here if upstream renames)
SEASONS = {2022: "2021-22", 2023: "2022-23", 2024: "2023-24", 2025: "2024-25", 2026: "2025-26"}
RAW = "https://raw.githubusercontent.com/ramirobentes/nba_pbp_data/main"
# Candidate upstream paths to try for each season's lineup-final file.
CANDIDATES = [
    "{raw}/data/lineup-final/{season}.csv",
    "{raw}/lineup-final/{season}.csv",
    "{raw}/data/lineup_final/{season}.csv",
]

def main():
    os.makedirs("pbp", exist_ok=True)
    ok = 0
    for ey, season in SEASONS.items():
        dest = os.path.join("pbp", f"lineup_{ey}.csv")
        if os.path.exists(dest):
            print(f"  [skip] {dest} already present")
            ok += 1
            continue
        got = False
        for tmpl in CANDIDATES:
            url = tmpl.format(raw=RAW, season=season)
            try:
                print(f"  [get ] {url}")
                urllib.request.urlretrieve(url, dest)
                sz = os.path.getsize(dest)
                if sz < 1000:   # not a real data file
                    os.remove(dest); continue
                print(f"         -> {dest} ({sz/1e6:.1f} MB)")
                got = True; ok += 1; break
            except Exception as e:
                continue
        if not got:
            print(f"  [MISS] could not fetch {season}. Download it manually from")
            print(f"         https://github.com/ramirobentes/nba_pbp_data and save as {dest}")
    print(f"\n{ok}/{len(SEASONS)} season files present in ./pbp/")
    if ok < len(SEASONS):
        sys.exit(1)

if __name__ == "__main__":
    main()
