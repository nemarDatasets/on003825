"""
Smoke test for on003825 stimuli alignment.

Loads every ``sub-*/eeg/*_events.tsv``, resolves stim_file via
``StimulusAligner``, and reports per-subject + total counts.

Run AFTER:
    python code/normalize_events_to_bids.py
    # plus: place the THINGS images under stimuli/<concept>/<file>.jpg
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_stimuli import StimulusAligner

ROOT_DEFAULT = Path(__file__).resolve().parent.parent


def run(root: Path = ROOT_DEFAULT) -> int:
    aligner = StimulusAligner(root)
    tsvs = sorted(root.glob('sub-*/eeg/sub-*_task-rsvp_events.tsv'))
    if not tsvs:
        print(f'No events.tsv files under {root}')
        return 1

    print(f'== smoke test on {len(tsvs)} subjects ==')
    failing: list[tuple[str, int]] = []
    total_rows = total_resolved = total_missing = total_targets = 0
    for p in tsvs:
        df = pd.read_csv(p, sep='\t')
        paths = aligner.paths_for_events(df)
        n_rows = len(df)
        n_targets = int((df.get('istarget', pd.Series(dtype=int)) == 1).sum())
        n_ok = sum(1 for x in paths if x is not None and x.exists())
        n_missing = sum(1 for x in paths if x is not None and not x.exists())
        sub = p.parts[-3]
        flag = '✓' if n_missing == 0 else '✗'
        print(f'  {flag} {sub}: rows={n_rows:5d}  resolved={n_ok:5d}  '
              f'missing={n_missing:3d}  targets={n_targets:4d}')
        if n_missing:
            failing.append((sub, n_missing))
        total_rows += n_rows
        total_resolved += n_ok
        total_missing += n_missing
        total_targets += n_targets

    print()
    print('== summary ==')
    print(f'   subjects        : {len(tsvs)}')
    print(f'   total rows      : {total_rows}')
    print(f'   resolved+exists : {total_resolved}')
    print(f'   resolved+missing: {total_missing}')
    print(f'   catch targets   : {total_targets}')
    if failing:
        print('\n== subjects with missing stimuli ==')
        for sub, n in failing:
            print(f'   {sub}: {n}')
    return 1 if total_missing else 0


if __name__ == '__main__':
    sys.exit(run())
