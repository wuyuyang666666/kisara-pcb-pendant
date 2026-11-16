#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终交付预览：正面 / 背面 并排 + 尺寸标注"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw

import effect as E

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
JS = os.path.join(ROOT, "build", "kisara_outline.json")
PPM = E.PPM


def back_render(d):
    W, H = d["size_mm"]
    poly = d["outline"]
    hole = d["mount_hole"]
    pad = 34
    size = (int(W * PPM) + pad * 2, int(H * PPM) + pad * 2)

    def T(pts):
        return [(pad + x * PPM, size[1] - pad - y * PPM) for x, y in pts]

    img = Image.new("RGB", size, (233, 231, 226))
    dr = ImageDraw.Draw(img)
    for i in range(0, size[1], 2):
        c = 229 + int(5 * math.sin(i / 43.0) + 3 * math.sin(i / 11.0))
        dr.line([(0, i), (size[0], i)], fill=(c, c - 2, c - 7))

    dr.polygon(T(poly), fill=E.BLACK)
    cx = d.get("axis_x", 27.65)
    heart = []
    for i in range(90):
        t = 2 * math.pi * i / 90
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        heart.append((cx + x * 0.46, 58.5 + y * 0.46))
    dr.polygon(T(heart), fill=E.GOLD)
    dr.polygon(T([(hole["cx"] + hole["d"] / 2 * math.cos(2 * math.pi * i / 48),
                   hole["cy"] + hole["d"] / 2 * math.sin(2 * math.pi * i / 48))
                  for i in range(48)]), fill=(238, 236, 231))
    dr.line(T(poly) + [T(poly)[0]], fill=(66, 66, 70), width=2, joint="curve")
    return img


def main():
    d = json.load(open(JS, encoding="utf-8"))
    front = E.render(path=None)
    back = back_render(d)

    W = front.width + back.width + 20
    H = max(front.height, back.height) + 54
    sheet = Image.new("RGB", (W, H), (250, 249, 246))
    sheet.paste(front, (0, 30))
    sheet.paste(back, (front.width + 20, 30))
    dr = ImageDraw.Draw(sheet)

    Wm, Hm = d["size_mm"]
    dr.text((10, 8), f"KISARA  PCB PENDANT   6L  ENIG  matte-black   "
                     f"{Wm:.1f} x {Hm:.1f} mm   mount hole D3.0", fill=(30, 30, 30))
    dr.text((10, H - 18), "FRONT  (gold line art + white silk highlight)", fill=(90, 90, 90))
    dr.text((front.width + 30, H - 18), "BACK  (gold heart  =  'Engage Kiss' contract mark)",
            fill=(90, 90, 90))
    p = os.path.join(ROOT, "assets", "final_preview.png")
    sheet.save(p)
    print("saved", p, sheet.size)


if __name__ == "__main__":
    main()
