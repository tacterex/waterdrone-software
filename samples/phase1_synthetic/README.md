# phase1_synthetic

Phase 1 of testing: correctness of the analysis app on abstract lakes generated with the same physics model the app uses.

| Folder | Contents |
|---|---|
| `config/` | One text file per model: lake boundary, origins of each parameter, survey settings. |
| `scripts/` | `generate_samples.py`: builds the CSV samples from the configs. |
| `reduced/` | Generated test samples (CSV in the waterdrone format). |

Regenerate everything: `python3 scripts/generate_samples.py`

Model: each origin is an isotropic point source, potential `w / r`; a parameter is the sum over its own origins; parameters are independent.

Survey patterns: regular lawnmower tracks (models 01-04) or a chaotic random walk with no grid structure (`model_01_single_origin_chaotic`: same lake and field as model 01, different sampling path).
