# phase2_real

Phase 2 of testing: real-world data, used to check the analysis app's visualization.

| Folder | Contents |
|---|---|
| `raw/` | Open-source samples exactly as downloaded. Never edited by hand. |
| `reduced/` | Parsed data in the same format the waterdrone produces. Generated from `raw/` by the scripts. |
| `scripts/` | Scripts that parse `raw/` into `reduced/`. |

## Workflow
1. Put a downloaded dataset in `raw/<dataset-name>/` together with a note on its source and license.
2. Run the matching parser from `scripts/`.
3. The output lands in `reduced/<dataset-name>/` and is what the analysis app is tested with.
