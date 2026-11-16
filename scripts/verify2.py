# -*- coding: utf-8 -*-
"""把自产的 Gerber 重新画回位图，用于校验（支持 G36 区域 / LPD·LPC / 圆孔径线）"""
import os, sys, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw

U = 1e6


def raster(path, ppm=12, box=(-31, -31, 31, 39)):
    x0, y0, x1, y1 = box
    W = int((x1 - x0) * ppm)
    H = int((y1 - y0) * ppm)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)

    def T(x, y):
        return ((x - x0) * ppm, (y1 - y) * ppm)

    aps = {}
    cur_ap = None
    pol = "D"
    region = None
    cx = cy = 0.0
    stats = {"regions": 0, "paths": 0, "flashes": 0, "pol_switches": 0}

    def val(tag, line):
        m = re.search(tag + r"(-?\d+)", line)
        return int(m.group(1)) / U if m else None

    with open(path, "r", encoding="ascii", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("%ADD"):
                m = re.match(r"%ADD(\d+)([A-Za-z]+),([\d.]+)", line)
                if m:
                    aps[int(m.group(1))] = float(m.group(3))
                continue
            if line.startswith("%LP"):
                p = line[3]
                if p != pol:
                    stats["pol_switches"] += 1
                pol = p
                continue
            if line.startswith("%") or line.startswith("G04"):
                continue
            if line.startswith("G36"):
                region = []
                continue
            if line.startswith("G37"):
                if region and len(region) >= 3:
                    d.polygon([T(*p) for p in region],
                              fill=255 if pol == "D" else 0)
                    stats["regions"] += 1
                region = None
                continue
            if line.startswith("D") and line.endswith("*") and len(line) <= 5:
                try:
                    cur_ap = int(line[1:-1])
                except ValueError:
                    pass
                continue
            if "D03" in line:
                x, y = val("X", line), val("Y", line)
                if x is None: x = cx
                if y is None: y = cy
                cx, cy = x, y
                ap = aps.get(cur_ap, 0.2) * ppm
                d.ellipse([T(x, y)[0] - ap / 2, T(x, y)[1] - ap / 2,
                           T(x, y)[0] + ap / 2, T(x, y)[1] + ap / 2],
                          fill=255 if pol == "D" else 0)
                stats["flashes"] += 1
                continue
            if "D01" in line or "D02" in line:
                x, y = val("X", line), val("Y", line)
                nx = cx if x is None else x
                ny = cy if y is None else y
                if region is not None:
                    # region 内所有端点都是顶点，D02 是轮廓起点，同样计入
                    region.append((nx, ny))
                else:
                    if "D01" in line:
                        w = max(1, int(round(aps.get(cur_ap, 0.2) * ppm)))
                        d.line([T(cx, cy), T(nx, ny)],
                               fill=255 if pol == "D" else 0, width=w)
                        stats["paths"] += 1
                cx, cy = nx, ny
                continue
    return img, stats


if __name__ == "__main__":
    base = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\build\gerber3"
    outdir = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets"
    for name in ("GTO", "GTS", "GKO", "GTL", "GBS", "G3"):
        p = os.path.join(base, f"kisara_medallion.{name}")
        img, st = raster(p, ppm=12)
        img.save(os.path.join(outdir, f"chk_{name}.png"))
        print(name, st, "ink px", int((np.asarray(img) > 127).sum()))
