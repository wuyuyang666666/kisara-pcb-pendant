#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参数试验 v3：只做开运算（去细丝），不做闭运算（不填缝）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import vectorize as V

SRC = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\Pure_black_solid_silhouette_of_2026-11-05T14-26-32.png"
OUT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\trials"
os.makedirs(OUT, exist_ok=True)
PX_PER_MM = 6


def render(poly, size_mm, label, ext_pts=None):
    w = int(size_mm[0] * PX_PER_MM) + 40
    h = int(size_mm[1] * PX_PER_MM) + 40
    img = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(img)
    for gx in range(0, int(size_mm[0]) + 1, 10):
        x = 20 + gx * PX_PER_MM
        d.line([(x, 20), (x, h - 20)], fill=(212, 212, 212))
    for gy in range(0, int(size_mm[1]) + 1, 10):
        y = h - 20 - gy * PX_PER_MM
        d.line([(20, y), (w - 20, y)], fill=(212, 212, 212))
    pts = [(20 + x * PX_PER_MM, h - 20 - y * PX_PER_MM) for x, y in poly]
    if len(pts) > 2:
        d.polygon(pts, fill=(26, 26, 28))
        d.line(pts + [pts[0]], fill=(210, 60, 60), width=1)
    d.rectangle([0, 0, w, 17], fill=(255, 255, 255))
    d.text((3, 3), label, fill=(0, 0, 0))
    return img


CASES = [
    ("O10",  0, 10),
    ("O14",  0, 14),
    ("O18",  0, 18),
    ("O22",  0, 22),
    ("O14c4", 4, 14),
]

panels = []
for name, cr, orr in CASES:
    bw, poly, st = V.build(SRC, name, target_width_mm=60.0,
                           close_r=cr, open_r=orr, rdp_eps=1.0, smooth=1)
    lab = f"{name}  {st['size_mm'][0]:.0f}x{st['size_mm'][1]:.0f}  minW={st['min_feature_mm']:.2f}"
    print(f"{name:8s} pts={st['points_final']:4d} minW={st['min_feature_mm']:.2f}mm "
          f"size={st['size_mm'][0]:.1f}x{st['size_mm'][1]:.1f}")
    panels.append(render(poly, st["size_mm"], lab))

W = sum(p.width for p in panels); H = max(p.height for p in panels)
sheet = Image.new("RGB", (W, H), (255, 255, 255))
x = 0
for p in panels:
    sheet.paste(p, (x, 0)); x += p.width
sheet.save(os.path.join(OUT, "compare_v3.png"))
print("saved", sheet.size)
