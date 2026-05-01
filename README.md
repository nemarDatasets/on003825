[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.on003825-blue)](https://doi.org/10.82901/nemar.on003825)

Experiment Details
Human electroencephalography recordings from 50 subjects for 1,854 concepts and 22,248 images in the THINGS stimulus database.
Images were presented in rapid serial visual presentation streams at 10Hz rates. Participants performed an orthogonal fixation colour change detection task.

Experiment length: 1 hour

## Stimuli

The 22,248 stimulus images are NOT bundled with this BIDS dataset: the
THINGS image archive (Hebart et al. 2019) is licensed for research /
non-commercial use and may not be redistributed without consent of the
copyright owners. Acquire the archive directly from the canonical OSF
project (https://osf.io/jum2f/, file `images_THINGS.zip`, ~5 GB,
password documented at osf.io/j6a3m), and unpack it under
`stimuli/<concept>/<file>.jpg`.

Once the images are in place, every events.tsv `stim_file` column entry
resolves to a real file. Two helpers are provided:

```bash
# 1) one-off normalisation: rewrites events.tsv to BIDS-canonical form
#    (adds stim_file, drops stim/stimname, converts onset/duration to seconds)
python code/normalize_events_to_bids.py

# 2) sanity check after stimuli are placed
python code/smoke_test.py
```

```python
import pandas as pd
from code.align_stimuli import StimulusAligner

aligner = StimulusAligner('.')
events = pd.read_csv('sub-01/eeg/sub-01_task-rsvp_events.tsv', sep='\t')
paths = aligner.paths_for_events(events)   # list[Path | None]
```

See `stimuli/README` for the license terms and `stimuli/stim-things_image.json`
for the BIDS stimulus sidecar.