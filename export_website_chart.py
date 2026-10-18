"""Build a static chart snapshot once; website visitors never read raw CSVs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

try:
    import duckdb
    import plotly
except ImportError:
    isolated = Path(__file__).resolve().parent / '.venv-raw-viewer' / 'Scripts' / 'python.exe'
    if isolated.is_file() and Path(sys.executable).resolve() != isolated.resolve():
        raise SystemExit(subprocess.call([str(isolated), '-B', str(Path(__file__).resolve()), *sys.argv[1:]]))
    raise SystemExit('Install requirements-viewer.txt before exporting.')

from plot_matched_ticks import build_matched, pairs_from
from plot_raw_ticks import DAY, ROOT, inventory
from plotly.offline import get_plotlyjs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'ticks')
    parser.add_argument('--points', type=int, default=6000, help='Display budget per pair; matching always precedes sampling')
    args = parser.parse_args()
    if not 100 <= args.points <= 100000:
        parser.error('--points must be between 100 and 100000')
    contracts = inventory(args.input.resolve())
    if not contracts:
        parser.error('No tick CSVs found')
    days = [day for entries in contracts.values() for day, _ in entries]
    result = build_matched(pairs_from(contracts), min(days), max(days) + DAY,
                           args.points, ROOT / '.cache' / 'matched-viewer')
    snapshot = {
        'version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'start': result['start'], 'end': result['end'],
        'matching': 'far-minus-near; latest far at or before near; 0 <= age < 1000 ms',
        'display': 'First/minimum-spread/maximum-spread/last original matches per bucket; zoom uses saved observations only',
        'point_budget_per_pair': args.points, 'total_matches': result['total_raw_rows'],
        'pairs': [{
            'symbol': c['symbol'], 'sampled': c['sampled'],
            'matches': c['raw_rows_in_window'],
            'rows': [[r[0], r[1], r[5], r[6]] for r in c['ticks']]
        } for c in result['contracts'] if c['ticks']]
    }
    destination = ROOT / 'website' / 'data'
    destination.mkdir(exist_ok=True)
    target = destination / 'spreads.json'
    temporary = target.with_suffix('.part')
    temporary.write_text(json.dumps(snapshot, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    temporary.replace(target)
    vendor = ROOT / 'website' / 'vendor'
    vendor.mkdir(exist_ok=True)
    (vendor / 'plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    print(f'Saved {len(snapshot["pairs"])} pairs, {sum(len(p["rows"]) for p in snapshot["pairs"]):,} points to {target}', flush=True)


if __name__ == '__main__':
    main()
