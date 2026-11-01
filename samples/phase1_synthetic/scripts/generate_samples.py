#!/usr/bin/env python3
"""Generate synthetic phase-1 test samples from a lake model config.

Physics model: every parameter is a sum of independent point sources (origins).
Each origin is an isotropic point source of Poisson's equation, so its potential is

    phi(r) = w / r

with w the origin weight and r the 3D distance from the origin to the sample.
The value of a parameter at a sample is the sum over the origins of THAT parameter
only; origins of different parameters never interact.

A survey is simulated inside the lake boundary, at constant speed, one sample per
SAMPLE_INTERVAL_S. The sample depth Z oscillates smoothly between Z_MIN and Z_MAX.
Two survey patterns (config key PATTERN):
  lawnmower  parallel east-west track lines (default, regular grid)
  chaotic    correlated random walk: the heading wanders randomly, the boat turns away
             from the shore; reproducible with SEED. No grid structure at all.

Output CSV (same layout as the phase-2 reduced data):
    TIMESTAMP (Unix s), LATITUDE, LONGITUDE (deg), Z (m below water surface), <PARAMS...>

Geometry uses a local flat projection around the boundary centroid (metres), which
is accurate to well below a metre for lakes of a few kilometres.

Usage:
    python3 generate_samples.py                      # all ../config/*.txt -> ../reduced/
    python3 generate_samples.py CONFIG.txt [...] [--out DIR]

Config format: see ../config/README.md
"""
import argparse
import csv
import glob
import math
import os
import random
import sys

R_EARTH = 6371000.0
M_PER_DEG = math.pi / 180.0 * R_EARTH
EDGE_MARGIN_M = 5.0  # survey lines stop this far inside the shore


def parse_config(path):
    cfg = {"boundary": [], "origins": {}, "name": os.path.splitext(os.path.basename(path))[0]}
    scalars = {"START_TIME": int, "SPEED_MS": float, "SAMPLE_INTERVAL_S": int,
               "TRACK_SPACING_M": float, "Z_MIN": float, "Z_MAX": float, "Z_PERIOD_S": float,
               "DURATION_S": int, "TURN_SIGMA_DEG": float, "SEED": int}
    cfg.update({"PATTERN": "lawnmower", "SEED": 0, "TURN_SIGMA_DEG": 15.0})
    optional = {"PATTERN", "SEED", "TURN_SIGMA_DEG", "TRACK_SPACING_M", "DURATION_S"}
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            tok = line.split()
            key, args = tok[0].upper(), tok[1:]
            try:
                if key == "BOUNDARY":
                    cfg["boundary"].append((float(args[0]), float(args[1])))
                elif key == "ORIGIN":
                    param = args[0].upper()
                    lat, lon, depth, w = map(float, args[1:5])
                    cfg["origins"].setdefault(param, []).append((lat, lon, depth, w))
                elif key == "PATTERN":
                    cfg["PATTERN"] = args[0].lower()
                    if cfg["PATTERN"] not in ("lawnmower", "chaotic"):
                        raise ValueError("PATTERN must be lawnmower or chaotic")
                elif key in scalars:
                    cfg[key] = scalars[key](args[0])
                else:
                    raise ValueError(f"unknown key {key}")
            except (IndexError, ValueError) as e:
                sys.exit(f"{path}:{n}: bad line {line!r} ({e})")
    needed = [k for k in scalars if k not in optional]
    needed.append("TRACK_SPACING_M" if cfg["PATTERN"] == "lawnmower" else "DURATION_S")
    for k in needed:
        if k not in cfg:
            sys.exit(f"{path}: missing {k} (needed for PATTERN {cfg['PATTERN']})")
    if len(cfg["boundary"]) < 3:
        sys.exit(f"{path}: BOUNDARY needs at least 3 points")
    if not cfg["origins"]:
        sys.exit(f"{path}: no ORIGIN lines")
    if cfg["Z_MIN"] > cfg["Z_MAX"]:
        sys.exit(f"{path}: Z_MIN > Z_MAX")
    return cfg


class Projection:
    def __init__(self, pts):
        self.lat0 = sum(p[0] for p in pts) / len(pts)
        self.lon0 = sum(p[1] for p in pts) / len(pts)
        self.kx = M_PER_DEG * math.cos(math.radians(self.lat0))

    def fwd(self, lat, lon):
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * M_PER_DEG

    def inv(self, x, y):
        return self.lat0 + y / M_PER_DEG, self.lon0 + x / self.kx


def inside(poly, x, y):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def survey_path(poly, spacing):
    """Waypoints of east-west lines clipped to the polygon, alternating direction."""
    ymin = min(p[1] for p in poly)
    ymax = max(p[1] for p in poly)
    pts, flip = [], False
    y = ymin + spacing / 2
    while y < ymax:
        xs = []
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            if (y1 > y) != (y2 > y):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        segs = [(xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2)]
        if flip:
            segs = [(b, a) for a, b in reversed(segs)]
        for a, b in segs:
            m = EDGE_MARGIN_M if b > a else -EDGE_MARGIN_M
            if abs(b - a) > 2 * EDGE_MARGIN_M:
                pts += [(a + m, y), (b - m, y)]
        flip = not flip
        y += spacing
    return pts


def sample_track(waypoints, speed, dt):
    """Points at constant speed along the waypoint polyline, one per dt seconds."""
    step = speed * dt
    out, carry = [], 0.0  # carry = distance already travelled since last sample
    out.append(waypoints[0])
    for (x1, y1), (x2, y2) in zip(waypoints, waypoints[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        d = step - carry
        while d <= L:
            t = d / L
            out.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
            d += step
        carry = L - (d - step)
    return out


def edge_distance(poly, x, y):
    best = float("inf")
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def chaotic_track(poly, speed, dt, n, sigma_deg, seed):
    """Correlated random walk inside the polygon (always >= EDGE_MARGIN_M from the shore)."""
    rng = random.Random(seed)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    while True:  # random start point inside the lake
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if inside(poly, x, y) and edge_distance(poly, x, y) >= EDGE_MARGIN_M:
            break
    heading, step, out = rng.uniform(0, 2 * math.pi), speed * dt, []
    sigma = math.radians(sigma_deg)
    for _ in range(n):
        out.append((x, y))
        h = heading + rng.gauss(0, sigma)
        for _try in range(100):  # near the shore: pick a new direction until the step is valid
            nx, ny = x + step * math.cos(h), y + step * math.sin(h)
            if inside(poly, nx, ny) and edge_distance(poly, nx, ny) >= EDGE_MARGIN_M:
                break
            h = rng.uniform(0, 2 * math.pi)
        else:
            nx, ny = x, y
        heading, x, y = h, nx, ny
    return out


def generate(cfg, out_path):
    proj = Projection(cfg["boundary"])
    poly = [proj.fwd(*p) for p in cfg["boundary"]]
    params = sorted(cfg["origins"])
    origins = {p: [(*proj.fwd(lat, lon), depth, w) for lat, lon, depth, w in cfg["origins"][p]]
               for p in params}

    if cfg["PATTERN"] == "chaotic":
        track = chaotic_track(poly, cfg["SPEED_MS"], cfg["SAMPLE_INTERVAL_S"],
                              cfg["DURATION_S"] // cfg["SAMPLE_INTERVAL_S"],
                              cfg["TURN_SIGMA_DEG"], cfg["SEED"])
    else:
        track = [p for p in sample_track(survey_path(poly, cfg["TRACK_SPACING_M"]),
                                         cfg["SPEED_MS"], cfg["SAMPLE_INTERVAL_S"])
                 if inside(poly, *p)]
    zmin, zmax, period = cfg["Z_MIN"], cfg["Z_MAX"], cfg["Z_PERIOD_S"]

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["TIMESTAMP", "LATITUDE", "LONGITUDE", "Z"] + params)
        for i, (x, y) in enumerate(track):
            t = cfg["START_TIME"] + i * cfg["SAMPLE_INTERVAL_S"]
            z = zmin + (zmax - zmin) * 0.5 * (1 + math.sin(2 * math.pi * (t - cfg["START_TIME"]) / period))
            vals = []
            for p in params:
                s = 0.0
                for ox, oy, oz, weight in origins[p]:
                    r = math.sqrt((x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2)
                    s += weight / r
                vals.append(s)
            lat, lon = proj.inv(x, y)
            w.writerow([t, f"{lat:.7f}", f"{lon:.7f}", f"{z:.3f}"] + [f"{v:.9g}" for v in vals])
    return len(track)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("configs", nargs="*", help="config files (default: all ../config/*.txt)")
    ap.add_argument("--out", default=os.path.join(here, "..", "reduced"), help="output directory")
    args = ap.parse_args()
    configs = args.configs or sorted(glob.glob(os.path.join(here, "..", "config", "*.txt")))
    if not configs:
        sys.exit("no config files found")
    os.makedirs(args.out, exist_ok=True)
    for c in configs:
        cfg = parse_config(c)
        out = os.path.join(args.out, cfg["name"] + ".csv")
        n = generate(cfg, out)
        print(f"{c} -> {out}: {n} samples, parameters {sorted(cfg['origins'])}")


if __name__ == "__main__":
    main()
