#!/usr/bin/env python3
"""Reduce the Utah Lake mapping workbook to the waterdrone CSV format.

Input : Utah_Lake_Mapping_Data.xlsx  (raw/)
Output: CSV with columns
        TIMESTAMP   - Unix time, integer seconds (UTC)
        LATITUDE    - decimal degrees (WGS 84)
        LONGITUDE   - decimal degrees (WGS 84)
        Z           - depth of the measurement in metres (0 = water surface), constant --z
        <PARAMS>    - concentration-related parameters, UPPER_CASE names

Only parameters that are a concentration (or are proportional to one) are kept.
pH and temperature are also kept because they are tied to concentrations (H+ activity,
temperature-dependent solubility/sensor response). Other absolute-value parameters
(conductivity, salinity, DO % saturation, transmittance, attenuation, turbidity, pH in mV)
are dropped. Edit KEEP below to change that.

Cleaning:
  * rows without a timestamp are dropped (empty trailing rows in the sheet)
  * rows with missing or implausible GPS coordinates are dropped (the raw GPS has
    glitches such as -11.8 instead of -111.8); plausible = within --max-dev degrees
    of the median position
  * rows where every kept parameter is empty are dropped
  * empty parameter cells stay empty in the CSV (e.g. nitrate at the start of the run)

Usage:
    python3 reduce_utah_lake.py INPUT.xlsx OUTPUT.csv [--sheet 20secMed]
                                [--utc-offset-hours -8] [--max-dev 0.5] [--z 0]
"""
import argparse
import csv
import statistics
import sys
from datetime import timedelta, timezone

import openpyxl

# raw column header -> output column name. Order here = order in the CSV.
KEEP = {
    "TSG Temp (degC)": "TSG_TEMP",           # water temperature, flow-through TSG, degC
    "EXO Temp (degC)": "EXO_TEMP",           # water temperature, EXO sonde, degC
    "EXO pH": "PH",                          # pH, standard units (-log10 of H+ activity)
    "WS fDOM (QSE)": "WS_FDOM",              # dissolved organic matter, QSE
    "WS fCHLA (µg/L)": "WS_FCHLA",           # chlorophyll-a, ug/L
    "NO3 (mg/L)": "NO3",                     # nitrate+nitrite as N, mg/L
    "DUV 310/452 (counts)": "DUV_310_452",   # fluorescence counts (~ fluorophore conc.)
    "DUV 280/452 (counts)": "DUV_280_452",
    "DUV 280/350 (counts)": "DUV_280_350",
    "EXO DO (mg/L)": "EXO_DO",               # dissolved oxygen, mg/L
    "EXO fDOM (QSE)": "EXO_FDOM",            # dissolved organic matter, QSE
    "EXO fCHLA (µg/L)": "EXO_FCHLA",         # chlorophyll-a, ug/L
    "EXO fBGAPC (µg/L)": "EXO_FBGAPC",       # phycocyanin, ug/L
}
# "NO3 (µM)" is deliberately skipped: it is NO3 (mg/L) * 71.39, the same quantity.


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--sheet", default="20secMed",
                    help="worksheet to read (default: 20secMed, 1 s spacing; 30secAvg is also available)")
    ap.add_argument("--utc-offset-hours", type=float, default=-8.0,
                    help="timezone of the raw timestamps (default -8: the data dictionary says PST)")
    ap.add_argument("--max-dev", type=float, default=0.5,
                    help="max degrees from the median position for a GPS fix to be accepted")
    ap.add_argument("--z", type=float, default=0.0,
                    help="depth of the measurements in metres, written to column Z (default 0)")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.input, read_only=True, data_only=True)
    if args.sheet not in wb.sheetnames:
        sys.exit(f"sheet {args.sheet!r} not found; available: {wb.sheetnames}")
    rows = wb[args.sheet].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]

    def col(name):
        if name not in header:
            sys.exit(f"column {name!r} not found in sheet; header is {header}")
        return header.index(name)

    i_ts, i_lat, i_lon = col("Time stamp"), col("Latitude"), col("Longitude")
    idx = [col(k) for k in KEEP]

    def num(v):
        # keep only real numbers (formula strings or text become empty)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    data = [r for r in rows if r[i_ts] is not None]
    fixes = [(num(r[i_lat]), num(r[i_lon])) for r in data]
    lats = [a for a, b in fixes if a is not None and b is not None]
    lons = [b for a, b in fixes if a is not None and b is not None]
    if not lats:
        sys.exit("no GPS fixes found")
    lat0, lon0 = statistics.median(lats), statistics.median(lons)

    tz = timezone(timedelta(hours=args.utc_offset_hours))
    out, dropped_gps, dropped_empty = [], 0, 0
    for r, (lat, lon) in zip(data, fixes):
        if lat is None or lon is None or abs(lat - lat0) > args.max_dev or abs(lon - lon0) > args.max_dev:
            dropped_gps += 1
            continue
        vals = [num(r[i]) for i in idx]
        if all(v is None for v in vals):
            dropped_empty += 1
            continue
        ts = int(r[i_ts].replace(tzinfo=tz).timestamp())
        out.append([ts, lat, lon, args.z] + vals)

    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["TIMESTAMP", "LATITUDE", "LONGITUDE", "Z"] + list(KEEP.values()))
        for row in out:
            w.writerow(["" if v is None else (repr(v) if isinstance(v, float) else v) for v in row])

    print(f"sheet {args.sheet}: {len(data)} rows with timestamp -> {len(out)} written "
          f"(dropped: {dropped_gps} bad/missing GPS, {dropped_empty} no parameter data)")


if __name__ == "__main__":
    main()
