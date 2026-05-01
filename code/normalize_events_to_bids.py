r"""
Lightly normalise on003825 events.tsv files toward BIDS conformance,
without breaking the validator's existing pass.

What this script does
---------------------
1. Convert ``onset`` and ``duration`` from samples (sfreq=1000) to seconds.
   BIDS requires both columns in seconds.
2. Replace Windows backslashes in the ``stim`` column with forward slashes
   (purely cross-platform cosmetic — the data is unchanged).
3. Rewrite each events.tsv atomically (tmp file + ``os.replace``).
4. Update ``task-rsvp_events.json`` (the existing dataset-level events sidecar)
   with proper ``Units`` for onset/duration and tightened descriptions, so the
   validator stops emitting ``TSV_ADDITIONAL_COLUMNS_UNDEFINED`` warnings.

What this script deliberately does NOT do
-----------------------------------------
- It does **not** introduce a BIDS-canonical ``stim_file`` column. Doing so
  triggers ``STIMULUS_FILE_MISSING`` errors in CI because the THINGS image
  archive is research-licensed and cannot be redistributed inside the
  dataset's repo. The legacy ``stim`` column carries the same info but the
  BIDS validator does not try to resolve it.
- It does **not** create a root-level ``events.json``; the existing
  ``task-rsvp_events.json`` is the single inheritable sidecar (BIDS principle).

Idempotent: re-running on already-normalised files is a no-op.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT_DEFAULT = Path(__file__).resolve().parent.parent
SAMPLE_RATE_HZ = 1000  # SamplingFrequency in every sub-*_task-rsvp_eeg.json

# Per-column metadata for /task-rsvp_events.json. The original dataset already
# ships a sidecar with most of these — we just tighten descriptions and add
# Units to the time-valued columns.
TASK_RSVP_EVENTS_JSON: dict = {
    "onset": {
        "Description": "Event onset relative to recording start.",
        "Units": "s",
    },
    "duration": {
        "Description": "Stimulus duration.",
        "Units": "s",
    },
    "eventnumber": {"Description": "Sequential event index within the run (0-based)."},
    "objectnumber": {"Description": "Concept index in the THINGS database (1-1854)."},
    "object": {"Description": "Concept name from THINGS, e.g. 'carousel'."},
    "stim": {
        "Description": (
            "Path of the stimulus image relative to the dataset root, e.g. "
            "'stimuli/carousel/carousel_11s.jpg'. Forward slashes. The "
            "image archive is provided separately under the THINGS license."
        ),
    },
    "stimname": {"Description": "Bare filename of the stimulus image."},
    "sequencenumber": {"Description": "Sequence index within the run."},
    "presentationnumber": {"Description": "Presentation index within the sequence."},
    "blocksequencenumber": {"Description": "Sequence index within the current block."},
    "withinsequencenumber": {"Description": "Position within the 20-image sequence."},
    "stimnumber": {"Description": "Image instance index within the concept (1-12)."},
    "isteststim": {
        "Description": "1 if the trial belongs to the held-out validation set, else 0.",
    },
    "teststimnumber": {
        "Description": "Index in the validation image set (0-199), or -1 for non-test trials.",
    },
    "istarget": {
        "Description": "Catch-trial flag.",
        "Levels": {
            "0": "Standard image presentation.",
            "1": "Catch target requiring a button press.",
        },
    },
    "response": {"Description": "Recorded button-press response (1 = pressed, 0 = none)."},
    "rt": {
        "Description": "Reaction time relative to last target event.",
        "Units": "s",
    },
    "correct": {"Description": "1 if the participant correctly identified the catch target, else 0."},
    "time_stimon": {
        "Description": "Stimulus on-time measured by the experimental software (independent clock).",
        "Units": "s",
    },
    "time_stimoff": {
        "Description": "Stimulus off-time measured by the experimental software (independent clock).",
        "Units": "s",
    },
    "stimdur": {
        "Description": "Measured stimulus duration (off - on).",
        "Units": "s",
    },
    "StimulusPresentation": {"SoftwareName": "Psychtoolbox-3"},
}


def _normalise_stim_value(s: object) -> object:
    """Replace backslashes with forward slashes; preserve missing values."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return s
    return str(s).replace('\\', '/')


def _looks_already_normalised(df: pd.DataFrame) -> bool:
    """A row whose onset is way past 1 hour (3600 s) almost certainly still
    carries the unconverted sample-count value. Sample-count onsets are
    in the thousands; second-valued onsets stay below ~3600 for a 1-h
    experiment. Use the max as a robust signal.
    """
    if 'onset' not in df.columns:
        return True
    try:
        return float(df['onset'].max()) < 3600.0 * 2
    except (TypeError, ValueError):
        return True


def rewrite_events_tsv(path: Path) -> bool:
    df = pd.read_csv(path, sep='\t')
    if 'stim' not in df.columns:
        return False  # nothing to convert

    changed = False

    if not _looks_already_normalised(df):
        # Convert sample-indexed onset/duration to seconds.
        if pd.api.types.is_numeric_dtype(df['onset']):
            df['onset'] = df['onset'] / SAMPLE_RATE_HZ
            changed = True
        if pd.api.types.is_numeric_dtype(df.get('duration', pd.Series(dtype=float))):
            df['duration'] = df['duration'] / SAMPLE_RATE_HZ

    if df['stim'].astype(str).str.contains('\\\\', regex=True).any():
        df['stim'] = df['stim'].map(_normalise_stim_value)
        changed = True

    if not changed:
        return False

    tmp = path.with_suffix(path.suffix + '.tmp')
    df.to_csv(tmp, sep='\t', index=False, na_rep='n/a')
    os.replace(tmp, path)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(ROOT_DEFAULT),
                    help='dataset root (default: parent of code/)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = Path(args.root)

    tsvs = sorted(root.glob('sub-*/eeg/sub-*_task-rsvp_events.tsv'))
    n_changed = 0
    for p in tsvs:
        if args.dry_run:
            df = pd.read_csv(p, sep='\t')
            need = (
                'stim' in df.columns
                and (
                    df['stim'].astype(str).str.contains('\\\\', regex=True).any()
                    or not _looks_already_normalised(df)
                )
            )
            print(f'  {"would rewrite" if need else "skip"}  {p.relative_to(root)}')
            n_changed += int(need)
            continue
        if rewrite_events_tsv(p):
            n_changed += 1
            print(f'  rewrote {p.relative_to(root)}')
    print(f'== events.tsv: {n_changed}/{len(tsvs)} updated ==')

    out_json = root / 'task-rsvp_events.json'
    if not args.dry_run:
        out_json.write_text(json.dumps(TASK_RSVP_EVENTS_JSON, indent=2) + '\n')
        print(f'== wrote {out_json.relative_to(root)} ==')


if __name__ == '__main__':
    main()
