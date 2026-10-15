[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.on003825-blue)](https://doi.org/10.82901/nemar.on003825)

Experiment Details
Human electroencephalography recordings from 50 subjects for 1,854 concepts and 22,248 images in the THINGS stimulus database.
Images were presented in rapid serial visual presentation streams at 10Hz rates. Participants performed an orthogonal fixation colour change detection task.

Experiment length: 1 hour

## Stimuli

The stimulus images are included in this dataset under `stimuli/<concept>/<file>.jpg`: the 26,107 images of the
THINGS image database (Hebart et al. 2019; 1,854 concepts), of which the events of the 50 participants use 22,448
distinct images. They are redistributed here with permission obtained by the NEMAR curator of this dataset (Bruno Aristimunha) for the THINGS image database, whose licence otherwise forbids redistribution without the consent of the copyright owners. Use of the images remains limited to research and education (THINGS licence,
https://osf.io/52wrx/download); the images are not covered by this dataset's licence.

The `stim` column of every `*_events.tsv` gives the image path relative to the dataset root (for example
`stimuli/carousel/carousel_11s.jpg`), and `stimname` its file name; all 22,448 paths resolve to a file under
`stimuli/`. `code/smoke_test.py` checks this on a local copy, and `code/align_stimuli.py` maps events rows to paths:

```python
import pandas as pd
from code.align_stimuli import StimulusAligner

aligner = StimulusAligner('.')
events = pd.read_csv('sub-01/eeg/sub-01_task-rsvp_events.tsv', sep='\t')
paths = aligner.paths_for_events(events)   # list[Path | None]
```

See `stimuli/README` for the licence terms and `stimuli/stim-things_image.json` for the BIDS stimulus sidecar.