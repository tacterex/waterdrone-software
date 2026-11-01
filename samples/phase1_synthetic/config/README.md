# config

One text file per lake model. `../scripts/generate_samples.py` turns each file into a CSV in `../reduced/` with the same name.

## Format
Line based; `#` starts a comment; keys are case-insensitive.

| Line | Meaning |
|---|---|
| `BOUNDARY lat lon` | One vertex of the lake outline (degrees). Repeat at least 3 times, in order around the lake. |
| `ORIGIN PARAM lat lon depth weight` | A point source of parameter `PARAM`: position (degrees), depth below the water surface (m, 15-50), weight `w` (potential is `w / r`, r in metres). Several origins per parameter are summed; different parameters are independent. |
| `START_TIME` | Unix time (s) of the first sample. |
| `SPEED_MS` | Boat speed along the track (m/s). |
| `SAMPLE_INTERVAL_S` | Seconds between samples (integer). |
| `PATTERN` | Survey pattern: `lawnmower` (default, regular parallel lines) or `chaotic` (random walk, no grid). |
| `TRACK_SPACING_M` | `lawnmower` only: distance between parallel east-west survey lines (m). |
| `DURATION_S` | `chaotic` only: survey length in seconds (number of samples = `DURATION_S / SAMPLE_INTERVAL_S`). |
| `TURN_SIGMA_DEG` | `chaotic` only: random heading change per sample (deg); smaller = straighter legs. Default 15. |
| `SEED` | `chaotic` only: random seed, makes the path reproducible. Default 0. |
| `Z_MIN`, `Z_MAX` | Range of the sample depth (m below surface), 1-10 here. |
| `Z_PERIOD_S` | Period (s) of the smooth up/down oscillation of the sample depth. |

The expected result of every sample is fully determined by the `ORIGIN` lines, so the analysis app can be checked against them.
