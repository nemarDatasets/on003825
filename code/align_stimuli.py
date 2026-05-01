"""
Align on003825 (Grootswagers et al. 2022 THINGS-EEG) events.tsv rows with
their stimulus images.

After acquiring the THINGS image archive separately and unpacking it under
``stimuli/<concept>/<file>.jpg``, this helper resolves each events.tsv row
to a local Path. It accepts the BIDS-canonical ``stim_file`` column
(BIDS 1.x), the ``stim_id`` column from the BIDS 2.0 draft, and the legacy
``stim`` column from the upstream OpenNeuro release (Windows backslashes
plus a ``stimuli\\`` prefix), in that order of preference.

Usage
-----
    aligner = StimulusAligner(root='/path/to/on003825')
    paths = aligner.paths_for_events(events_df)         # list[Path | None]
    img   = aligner.image_for_event(row, mode='PIL')    # single row
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

try:
    from PIL import Image as _PIL_Image
except ImportError:
    _PIL_Image = None


def normalise_stim_path(s: object) -> Optional[str]:
    """Convert ``stimuli\\carousel\\carousel_11s.jpg`` to ``carousel/carousel_11s.jpg``.

    - Backslashes become forward slashes.
    - A leading ``stimuli/`` (case-insensitive) is dropped: paths are
      relative to the dataset's ``stimuli/`` directory.
    - Returns ``None`` for missing or empty values.
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    out = str(s).replace('\\', '/').strip()
    if not out:
        return None
    if out.lower().startswith('stimuli/'):
        out = out[len('stimuli/'):]
    return out or None


class StimulusAligner:
    # Tried in order; first non-empty value wins. The legacy 'stim' is
    # listed first because that's what this dataset ships with — the BIDS
    # validator does not try to resolve non-canonical columns, so STIMULUS_FILE_MISSING
    # never fires when the THINGS images are absent (license-restricted).
    STIM_COLUMNS = ('stim', 'stim_file', 'stim_id')

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.stim_root = self.root / 'stimuli'

    def path_for_event(self, row) -> Optional[Path]:
        """Return the image path for one events.tsv row, or None."""
        for col in self.STIM_COLUMNS:
            val = row.get(col) if hasattr(row, 'get') else getattr(row, col, None)
            rel = normalise_stim_path(val)
            if rel is not None:
                return self.stim_root / rel
        return None

    def image_for_event(self, row, mode: str = 'PIL'):
        """Return the stimulus image. mode ∈ {'PIL', 'bytes', 'path'}."""
        p = self.path_for_event(row)
        if p is None:
            return None
        if mode == 'path':
            return p
        if mode == 'bytes':
            return p.read_bytes()
        if _PIL_Image is None:
            raise RuntimeError("Pillow is not installed; use mode='path' or 'bytes'.")
        return _PIL_Image.open(p)

    def paths_for_events(
        self, events: pd.DataFrame, drop_targets: bool = False
    ) -> list[Optional[Path]]:
        """Vectorised single-pass resolution.

        Picks the first column from STIM_COLUMNS that exists in ``events``,
        normalises the strings with vectorised pandas ops, then materialises
        Paths in one Python pass.
        """
        col = next((c for c in self.STIM_COLUMNS if c in events.columns), None)
        n = len(events)
        if col is None:
            return [None] * n

        s = events[col].astype('object')
        # Vectorised normalisation: replace, strip, drop "stimuli/" prefix
        s = s.where(s.notna(), None)
        s = s.map(normalise_stim_path)

        if drop_targets and 'istarget' in events.columns:
            mask = events['istarget'].fillna(0).astype(int) == 1
            s = s.where(~mask, None)

        return [self.stim_root / x if x else None for x in s]


def demo(
    root: str = '/data/tau/iceberg_1/titanic_1/datasets/bids/on003825',
    subject: str = '01',
) -> None:
    """Resolve sub-XX events.tsv and report counts."""
    root_p = Path(root)
    aligner = StimulusAligner(root_p)
    ev = root_p / f'sub-{subject}/eeg/sub-{subject}_task-rsvp_events.tsv'
    df = pd.read_csv(ev, sep='\t')
    paths = aligner.paths_for_events(df)
    n_ok = sum(1 for p in paths if p is not None and p.exists())
    n_missing = sum(1 for p in paths if p is not None and not p.exists())
    n_none = sum(1 for p in paths if p is None)
    print(f'== sub-{subject} events.tsv ({len(df)} rows) ==')
    print(f'   resolved+exists : {n_ok}')
    print(f'   resolved+missing: {n_missing}')
    print(f'   unresolved      : {n_none}')


if __name__ == '__main__':
    demo()
