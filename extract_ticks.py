"""Extract downloaded tick ZIPs without downloading anything. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def extract(path, overwrite=False):
    checksum = path.with_name(path.name + '.CHECKSUM')
    verified = False
    if checksum.exists():
        fields = checksum.read_text(encoding='utf-8-sig').split()
        if not fields or digest(path) != fields[0].lower():
            raise ValueError('SHA-256 checksum mismatch')
        verified = True
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        expected_name = path.stem + '.csv'
        if len(members) != 1 or members[0].filename != expected_name:
            raise ValueError('Expected one CSV matching the ZIP name; extraction refused')
        member = members[0]
        output = path.with_suffix('.csv')
        if output.exists() and not overwrite:
            # Validate existing output against archive size + CRC before skipping.
            import zlib
            crc = 0
            size = 0
            with output.open('rb') as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b''):
                    size += len(block)
                    crc = zlib.crc32(block, crc)
            if size != member.file_size or crc != member.CRC:
                raise ValueError('Existing CSV differs from ZIP; use --overwrite to replace it')
            return {'zip': str(path), 'csv': str(output), 'status': 'verified_existing', 'sha256_verified': verified}
        temporary = output.with_name(output.name + '.extract.part')
        try:
            with archive.open(member) as source, temporary.open('wb') as destination:
                # Reading to EOF checks the member CRC; partial files never become CSVs.
                shutil.copyfileobj(source, destination, 1024 * 1024)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    return {'zip': str(path), 'csv': str(output), 'status': 'extracted', 'sha256_verified': verified}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parent / 'data' / 'ticks', help='Recursively search this directory')
    parser.add_argument('--overwrite', action='store_true', help='Replace existing CSVs after successful extraction')
    parser.add_argument('--dry-run', action='store_true', help='List ZIPs without extracting or writing reports')
    args = parser.parse_args()
    root = args.input.resolve()
    if not root.is_dir():
        parser.error(f'Input directory does not exist: {root}')
    archives = sorted(root.rglob('*-trades-*.zip'))
    if not archives:
        print(f'No tick-trade ZIPs found in {root}')
        return 1
    if args.dry_run:
        for path in archives:
            print(f'{path} -> {path.with_suffix(".csv")}')
        print(f'{len(archives)} archives; no files changed.')
        return 0
    results = []
    for index, path in enumerate(archives, 1):
        try:
            result = extract(path, args.overwrite)
        except Exception as error:
            result = {'zip': str(path), 'status': 'failed', 'error': str(error)}
        results.append(result)
        print(f'[{index}/{len(archives)}] {result["status"]}: {path}', flush=True)
        if result['status'] == 'failed':
            print(f'  {result["error"]}', file=sys.stderr)
    failures = sum(r['status'] == 'failed' for r in results)
    report = root / ('extract-report-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report.write_text(json.dumps({'run_utc': datetime.now(timezone.utc).isoformat(), 'failures': failures, 'files': results}, indent=2) + '\n', encoding='utf-8')
    print(f'Finished: {len(results) - failures} succeeded, {failures} failed. Report: {report}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
