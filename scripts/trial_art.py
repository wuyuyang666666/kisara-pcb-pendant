# -*- coding: utf-8 -*-
"""线稿提取参数试验：不同裁切 + 不同阈值"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import lineart as LA

SRC = r"C:\Users\rain\.workbuddy\clipboard-images\clipboard-2026-11-05T13-05-43-527Z-c930b2e8.jpg"
OUT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\lineart_trial.png"

CROPS = {
    "full": (0, 0, 1060, 1019),
    "head": (0, 0, 1060, 870),
    "tight": (90, 40, 980, 830),
}

PARAMS = [
    dict(t=24),
    dict(t=36),
    dict(t=52),
]

CELL = 420


def render_cell(img, paths, skel, label):
    """黑底白线，带裁切原图的灰度缩略作为参考不做，只画线"""
    h, w = skel.shape
    s = CELL / max(w, h)
    im = Image.new("RGB", (CELL, CELL), (18, 18, 20))
    d = ImageDraw.Draw(im)
    ox = (CELL - w * s) / 2
    oy = (CELL - h * s) / 2
    for pl in paths:
        xy = [(ox + x * s, oy + y * s) for x, y in pl]
        d.line(xy, fill=(240, 240, 240), width=1)
    d.text((6, CELL - 16), f"{label}  lines={len(paths)}", fill=(150, 220, 255))
    return im


def main():
    src = Image.open(SRC).convert("RGB")
    tiles = []
    for cname, box in CROPS.items():
        crop = src.crop(box)
        # 参考：原图缩略
        ref = crop.copy()
        ref.thumbnail((CELL, CELL))
        rc = Image.new("RGB", (CELL, CELL), (30, 30, 32))
        rc.paste(ref, ((CELL - ref.width) // 2, (CELL - ref.height) // 2))
        ImageDraw.Draw(rc).text((6, CELL - 16), cname, fill=(255, 210, 120))
        tiles.append(rc)
        for prm in PARAMS:
            paths, skel, mask = LA.build(crop, **prm)
            tiles.append(render_cell(crop, paths, skel,
                                     f"{cname} t={prm['t']}"))
            print(cname, prm, "paths", len(paths),
                  "px", int(skel.sum()))

    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * CELL, rows * CELL), (45, 45, 48))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * CELL, (i // cols) * CELL))
    sheet.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
