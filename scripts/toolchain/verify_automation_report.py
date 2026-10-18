#!/usr/bin/env python3
"""Check Unreal editor/client automation reports and selected native loading."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

NATIVE = 'SoraArena.Connect.NativeLoader'


def problems(report, log, selected, status, bridge, context='client'):
    issues = []
    tests = report.get('tests', [])
    names = [test.get('fullTestPath', '') for test in tests]
    found = re.findall(r"Found (\d+) automation tests based on '([^']*)'", log)
    if status:
        issues.append(f'{context} exited {status}')
    if not tests:
        issues.append(f"no tests matched '{selected}'")
    if len(found) != 1 or found[0][1].casefold() != selected.casefold() or int(found[0][0]) != len(tests):
        issues.append('reported test count does not match discovered tests')
    if len(set(names)) != len(names) or any(not name for name in names):
        issues.append('duplicate or unnamed automation results')
    prefixes = [name.casefold() for name in selected.split('+')]
    if any(not any(name.casefold().startswith(prefix) for prefix in prefixes) for name in names):
        issues.append('report includes tests outside the requested selection')
    if any(report.get(key, 0) for key in ('failed', 'notRun', 'inProcess')):
        issues.append('report contains failed or unfinished tests')
    for test in tests:
        events = [entry.get('event', {}) for entry in test.get('entries', [])]
        if (test.get('state') != 'Success' or test.get('errors', 0)
                or any(event.get('type') == 'Error' for event in events)):
            issues.append(f"unsuccessful test: {test.get('fullTestPath', '<unnamed>')}")
    if any(NATIVE.casefold().startswith(prefix) for prefix in prefixes):
        matches = [test for test in tests if test.get('fullTestPath') == NATIVE]
        if len(matches) != 1:
            issues.append('selected NativeLoader was not discovered and executed exactly once')
        else:
            messages = [entry.get('event', {}).get('message', '') for entry in matches[0].get('entries', [])]
            prefix = f'NativeLoader context={context} staged_library='
            paths = [message.removeprefix(prefix) for message in messages if message.startswith(prefix)]
            if len(paths) != 1 or Path(paths[0]).resolve() != bridge.resolve():
                issues.append(f'NativeLoader did not identify the actual {context} bridge path')
            if 'NativeLoader ABI=30 research_builder=1 join_inspector=1 join_signing_blocked=1 buy_signing_blocked=1' not in messages:
                issues.append('NativeLoader lacks ABI30 research-feature and signing-gate execution evidence')
    defaults = sorted(set(re.findall(
        r'LogMaterial: Warning: Material (\S+) missing usage flag (\w+)! Default Material will be used in game', log)))
    if defaults and context == 'client':
        issues.append(f'{len(defaults)} cooked materials lack usage flags: {defaults}')
    fatal = re.findall(r'^.*(?:Fatal error|=== Critical error|Assertion failed|Ensure condition failed|LogOutputDevice: Error).*$', log, re.MULTILINE)
    if fatal:
        issues.append(f'{len(fatal)} fatal, assertion or ensure lines during {context} automation')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path); parser.add_argument('log', type=Path)
    parser.add_argument('filter'); parser.add_argument('status', type=int)
    parser.add_argument('results', type=Path); parser.add_argument('bridge', type=Path)
    parser.add_argument('--context', choices=('editor', 'client'), default='client')
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding='utf-8-sig'))
        log = args.log.read_text(errors='replace')
        issues = problems(report, log, args.filter, args.status, args.bridge, args.context)
        rows = ['state\terrors\twarnings\tseconds\ttest']
        for test in sorted(report.get('tests', []), key=lambda item: item['fullTestPath']):
            events = [entry.get('event', {}) for entry in test.get('entries', [])]
            errors = max(test.get('errors', 0), sum(event.get('type') == 'Error' for event in events))
            warnings = max(test.get('warnings', 0), sum(event.get('type') == 'Warning' for event in events))
            row = f"{test.get('state', 'Unknown')}\t{errors}\t{warnings}\t{test.get('duration', 0):.2f}\t{test['fullTestPath']}"
            rows.append(row); print(row)
            for event in [event for event in events if event.get('type') == 'Error'][:5]:
                print('  ' + event.get('message', '')[:220])
        args.results.write_text('\n'.join(rows) + '\n')
        if issues:
            raise ValueError('; '.join(issues))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'FAIL {args.context} automation: {error}', file=sys.stderr)
        return 1
    print(f"PASS: {len(report['tests'])} {args.context} automation tests; report {args.report}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
