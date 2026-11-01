# reduced

Parsed data in the waterdrone data format, one subfolder or file per dataset.

Do not edit by hand: regenerate with the scripts in `../scripts/`.

## CSV format

One row per measurement. Empty cell = no reading.

| Column | Unit | Meaning |
|---|---|---|
| `TIMESTAMP` | s | Unix time (integer seconds, UTC) |
| `LATITUDE` | deg | WGS 84 decimal degrees |
| `LONGITUDE` | deg | WGS 84 decimal degrees |
| `Z` | m | Depth of the measurement, 0 = water surface |
| other columns | see below | One measured parameter each, UPPER_CASE names |

## Parameters in `Utah_Lake_20secMed.csv`

| Column | Unit | Explanation |
|---|---|---|
| `TSG_TEMP` | degC | Water temperature from the flow-through thermosalinograph. Temperature controls solubility of gases and reaction/sensor rates, so it conditions every concentration. |
| `EXO_TEMP` | degC | Water temperature from the EXO sonde; a second, independent reading of the same quantity. |
| `PH` | pH units | Acidity (negative log of hydrogen-ion activity), EXO sonde. It sets the speciation of dissolved chemicals, so it is tied to concentrations. |
| `WS_FDOM` | QSE | Fluorescent dissolved organic matter (WETStar sensor), in quinine sulfate equivalents. Proportional to the concentration of dissolved organic matter. |
| `WS_FCHLA` | ug/L | Chlorophyll-a (WETStar), temperature-corrected. Proxy for algae concentration. |
| `NO3` | mg/L | Nitrate plus nitrite as nitrogen, in situ, unfiltered. Not reported at the start of the run. |
| `DUV_310_452` | counts | Custom fluorescence sensor, excitation 310 nm, emission 452 nm. Signal grows with the concentration of fluorescent organic matter. |
| `DUV_280_452` | counts | Same sensor type, excitation 280 nm, emission 452 nm. |
| `DUV_280_350` | counts | Same sensor type, excitation 280 nm, emission 350 nm (protein-like fluorescence). |
| `EXO_DO` | mg/L | Dissolved oxygen concentration (EXO sonde). |
| `EXO_FDOM` | QSE | Fluorescent dissolved organic matter (EXO sonde); a second reading next to `WS_FDOM`. |
| `EXO_FCHLA` | ug/L | Chlorophyll-a estimate from in-vivo fluorescence (EXO sonde). |
| `EXO_FBGAPC` | ug/L | Phycocyanin (blue-green algae pigment) estimate from in-vivo fluorescence (EXO sonde). Proxy for cyanobacteria. |

Source: `raw/Utah_Lake_Mapping_Data.xlsx`. `Utah_Lake_20secMed.csv` comes from sheet `20secMed` (20 s median, 1 s spacing); `Utah_Lake_30secAvg.csv` from sheet `30secAvg` (30 s average, ~30 s spacing). Raw timestamps are PST per the data dictionary, converted to UTC.
