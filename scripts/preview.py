#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板框预览：把 mm 多边形渲染成可看的图，带网格与尺寸标注"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import math
from PIL import Image, ImageDraw, ImageFont
import build_shape as B

PX = 8
PAD = 40


def draw_poly(poly, size_mm, path, title="", grid=10, fill=(26, 26, 28),
              outline=(200, 60, 60), marks=None, notes=None):
    w = int(size_mm[0] * PX) + PAD * 2
    h = int(size_mm[1] * PX) + PAD * 2 + 24
    img = Image.new("RGB", (w, h), (246, 246, 244))
    d = ImageDraw.Draw(img)

    for gx in range(0, int(size_mm[0]) + 1, grid):
        x = PAD + gx * PX
        d.line([(x, PAD), (x, h - PAD)], fill=(220, 220, 218))
        d.text((x + 2, PAD - 12), str(gx), fill=(150, 150, 148))
    for gy in range(0, int(size_mm[1]) + 1, grid):
        y = h - PAD - gy * PX
        d.line([(PAD, y), (w - PAD, y)], fill=(220, 220, 218))
        d.text((PAD - 18, y - 5), str(gy), fill=(150, 150, 148))

    pts = [(PAD + x * PX, h - PAD - y * PX) for x, y in poly]
    if len(pts) > 2:
        d.polygon(pts, fill=fill)
        d.line(pts + [pts[0]], fill=outline, width=1)

    for m in (marks or []):
        cx, cy, r, col = m
        c = (PAD + cx * PX, h - PAD - cy * PX)
        d.ellipse([c[0] - r * PX, c[1] - r * PX, c[0] + r * PX, c[1] + r * PX],
                  outline=col, width=2)

    d.text((6, 6), title, fill=(20, 20, 20))
    y = h - 18
    for line in (notes or []):
        d.text((6, y), line, fill=(90, 90, 90))
        y += 12
    img.save(path)
    return img


if __name__ == "__main__":
    SRC = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\Pure_black_solid_silhouette_of_2026-11-05T14-26-32.png"
    OUT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets"
    for op in (8, 12, 16):
        bw, ring, poly, st = B.build(SRC, 60.0, open_px=op)
        p = os.path.join(OUT, f"shape_open{op}.png")
        draw_poly(poly, st["size_mm"], p,
                  title=f"open{op}px   {st['size_mm'][0]:.0f}x{st['size_mm'][1]:.0f}mm   "
                        f"minW={st['min_w_mm']:.2f}mm  pts={st['pts_final']}")
        print("saved", p, f"{st['size_mm'][0]:.1f}x{st['size_mm'][1]:.1f}")
