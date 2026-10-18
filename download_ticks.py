"""Download Binance USD-M individual trade ticks; standard library only."""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import zipfile

BASE = 'https://data.binance.vision/data/futures/um/daily/trades'
PREFIX = 'data/futures/um/daily/trades/'
BUCKET = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'


def listing(prefix, delimiter=None):
    """Read the official archive index, including every pagination page."""
    params = {'list-type': '2', 'prefix': prefix}
    if delimiter:
        params['delimiter'] = delimiter
    ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    while True:
        request = Request(BUCKET + '?' + urlencode(params), headers={'User-Agent': 'CalendarSpreadTicks/1.0'})
        with urlopen(request, timeout=60) as response:
            root = ET.fromstring(response.read())
        for element in root.findall('s:Contents/s:Key', ns):
            yield element.text
        for element in root.findall('s:CommonPrefixes/s:Prefix', ns):
            yield element.text
        if root.findtext('s:IsTruncated', namespaces=ns) != 'true':
            break
        token = root.findtext('s:NextContinuationToken', namespaces=ns)
        if not token:
            raise ValueError('Truncated archive listing has no continuation token')
        params['continuation-token'] = token


def discover_symbols(quarterly=None):
    result = []
    for key in listing(PREFIX + (quarterly + '_' if quarterly else ''), '/'):
        symbol = key.rstrip('/').rsplit('/', 1)[-1]
        pattern = re.escape(quarterly) + r'_\d{6}' if quarterly else r'[A-Z0-9]+(?:_\d{6})?'
        if re.fullmatch(pattern, symbol):
            result.append(symbol)
    return sorted(set(result))


def available_plan(symbols, start, end):
    """Only schedule published daily ZIPs within the requested dates."""
    for symbol in symbols:
        pattern = re.compile(re.escape(symbol) + r'-trades-(\d{4}-\d{2}-\d{2})\.zip')
        # A year prefix avoids scanning unrelated years for each contract.
        for year in range(start.year, end.year + 1):
            prefix = f'{PREFIX}{symbol}/{symbol}-trades-{year}-'
            for key in listing(prefix):
                match = pattern.fullmatch(key.rsplit('/', 1)[-1])
                if match and start <= date.fromisoformat(match[1]) <= end:
                    yield symbol, 'https://data.binance.vision/' + key


def transfer(url, destination):
    for attempt in range(4):
        try:
            request = Request(url, headers={'User-Agent': 'CalendarSpreadTicks/1.0'})
            with urlopen(request, timeout=60) as response, destination.open('wb') as handle:
                shutil.copyfileobj(response, handle, 1024 * 1024)
            return
        except HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def digest(file):
    result = hashlib.sha256()
    with file.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def download(url, folder, extract):
    folder.mkdir(parents=True, exist_ok=True)
    name = url.rsplit('/', 1)[1]
    target = folder / name
    checksum_part = folder / (name + '.CHECKSUM.part')
    part = folder / (name + '.part')
    try:
        transfer(url + '.CHECKSUM', checksum_part)
        fields = checksum_part.read_text(encoding='utf-8-sig').split()
        if not fields or not re.fullmatch(r'[0-9a-fA-F]{64}', fields[0]):
            raise ValueError('Invalid published checksum')
        expected = fields[0].lower()
        reused = target.exists()
        if reused:
            if digest(target) != expected:
                raise ValueError(f'Existing ZIP fails checksum: {target}. Move it aside before retrying.')
        else:
            transfer(url, part)
            if digest(part) != expected:
                raise ValueError('Downloaded ZIP fails checksum')
            part.replace(target)
        checksum_part.replace(folder / (name + '.CHECKSUM'))
        if extract:
            with zipfile.ZipFile(target) as archive:
                members = archive.infolist()
                csv_name = name[:-4] + '.csv'
                if len(members) != 1 or members[0].filename != csv_name:
                    raise ValueError('Unexpected ZIP contents; extraction refused')
                csv_part = folder / (csv_name + '.part')
                try:
                    with archive.open(members[0]) as source, csv_part.open('wb') as handle:
                        shutil.copyfileobj(source, handle, 1024 * 1024)
                    csv_part.replace(folder / csv_name)
                finally:
                    csv_part.unlink(missing_ok=True)
        return {'url': url, 'path': str(target), 'sha256': expected, 'bytes': target.stat().st_size,
                'status': 'verified_existing' if reused else 'downloaded', 'extracted': extract}
    finally:
        part.unlink(missing_ok=True)
        checksum_part.unlink(missing_ok=True)


def plan(symbols, start, end):
    day = start
    while day <= end:
        for symbol in symbols:
            yield symbol, f'{BASE}/{symbol}/{symbol}-trades-{day.isoformat()}.zip'
        if day == end:
            break
        day += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--symbols', nargs='+', help='Explicit contract symbols')
    selection.add_argument('--all-symbols', action='store_true', help='All archived USD-M symbols, including delisted contracts')
    selection.add_argument('--quarterly', nargs='?', const='BTCUSDT', help='All dated contracts for a base (default BTCUSDT)')
    parser.add_argument('--start', type=date.fromisoformat, required=True, help='Inclusive UTC date YYYY-MM-DD')
    parser.add_argument('--end', type=date.fromisoformat, required=True, help='Inclusive UTC date YYYY-MM-DD')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'data' / 'ticks')
    parser.add_argument('--extract', action='store_true', help='Also extract original CSVs')
    parser.add_argument('--skip-missing', action='store_true', help='Allow HTTP 404 archives; still record gaps')
    parser.add_argument('--dry-run', action='store_true', help='Print URLs only; discovery modes read archive listings, but download no data')
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('--start must be on or before --end')
    discovery = args.all_symbols or args.quarterly is not None
    if args.quarterly is not None:
        args.quarterly = args.quarterly.upper()
        if not re.fullmatch(r'[A-Z0-9]+', args.quarterly):
            parser.error('Expected a base symbol, e.g. BTCUSDT')
    if discovery:
        args.symbols = discover_symbols(args.quarterly)
        print(f'Discovered {len(args.symbols)} archived symbols.', file=sys.stderr)
    else:
        args.symbols = list(dict.fromkeys(s.upper() for s in args.symbols))
    if any(not re.fullmatch(r'[A-Z0-9]+(?:_\d{6})?', s) for s in args.symbols):
        parser.error('Invalid futures symbol')
    if not args.symbols:
        parser.error('No symbols found')
    jobs = available_plan(args.symbols, args.start, args.end) if discovery else plan(args.symbols, args.start, args.end)
    if args.dry_run:
        for _, url in jobs:
            print(url)
        return 0
    args.output = args.output.resolve()
    results, failures = [], 0
    for symbol, url in jobs:
        try:
            result = download(url, args.output / symbol, args.extract)
        except Exception as error:
            missing = isinstance(error, HTTPError) and error.code == 404
            result = {'url': url, 'status': 'missing' if missing else 'failed', 'error': str(error)}
            if not (missing and args.skip_missing):
                failures += 1
        results.append(result)
        print(f"{result['status']}: {url}", flush=True)
    if not results:
        print('No published trade archives found in this date range.', file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'run_utc': datetime.now(timezone.utc).isoformat(), 'market': 'USD-M futures',
              'dataset': 'trades', 'symbols': args.symbols, 'start_utc': args.start.isoformat(),
              'end_utc': args.end.isoformat(), 'failures': failures, 'files': results,
              'source': 'https://github.com/binance/binance-public-data/'}
    report_file = args.output / ('download-report-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_file.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Report: {report_file}; failures: {failures}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
