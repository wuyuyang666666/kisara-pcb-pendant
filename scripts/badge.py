#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""圆形徽章挂件效果渲染（三色分离版）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import math
from PIL import Image, ImageDraw, ImageFilter
import posterize as P

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
SRC = r"C:\Users\rain\.workbuddy\clipboard-images\clipboard-2026-11-05T13-05-43-527Z-c930b2e8.jpg"

PPM = 14
D_BOARD = 58.0
D_ART = 54.0
BLACK = (21, 21, 23)
GOLD = (204, 166, 96)
GOLD_HI = (238, 210, 152)
SILK = (243, 243, 241)


def render(dark_max=96, light_min=205, path=None, show_hole=True):
    gold, silk, _ = P.separate(SRC, target_mm=D_ART, dark_max=dark_max, light_min=light_min)

    pad = 40
    sz = int(D_BOARD * PPM) + pad * 2
    size = (sz, sz)
    img = Image.new("RGB", size, (232, 230, 225))
    d = ImageDraw.Draw(img)
    for i in range(0, sz, 2):
        c = 228 + int(5 * math.sin(i / 41.0) + 3 * math.sin(i / 9.0))
        d.line([(0, i), (sz, i)], fill=(c, c - 2, c - 7))

    def T(pts, ox=0.0, oy=0.0):
        return [(pad + (x + ox) * PPM, sz - pad - (y + oy) * PPM) for x, y in pts]

    board = Image.new("L", size, 0)
    ImageDraw.Draw(board).polygon(
        T([(D_BOARD / 2 + D_BOARD / 2 * math.cos(2 * math.pi * i / 96),
            D_BOARD / 2 + D_BOARD / 2 * math.sin(2 * math.pi * i / 96)) for i in range(96)]),
        fill=255)

    if show_hole:
        hx, hy = D_BOARD / 2, D_BOARD - 7.0
        hp = [(hx + 1.5 * math.cos(2 * math.pi * i / 48),
               hy + 1.5 * math.sin(2 * math.pi * i / 48)) for i in range(48)]
        ImageDraw.Draw(board).polygon(T(hp), fill=0)

    sh = board.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.28))
    img = Image.composite(Image.new("RGB", size, (143, 140, 133)), img, sh)
    img = Image.composite(Image.new("RGB", size, BLACK), img, board)

    off = (D_BOARD - D_ART) / 2.0
    for polys, color in ((gold, GOLD),):
        m = Image.new("L", size, 0)
        md = ImageDraw.Draw(m)
        for ring in polys:
            if len(ring) < 3:
                continue
            md.polygon(T(ring, off, off), fill=255)
        m = Image.composite(m, Image.new("L", size, 0), board)
        img = Image.composite(Image.new("RGB", size, color), img, m)

    ImageDraw.Draw(img).ellipse(
        [pad, pad, sz - pad, sz - pad], outline=(70, 70, 74), width=2)

    if path:
        img.save(path)
    return img


if __name__ == "__main__":
    p = os.path.join(ROOT, "assets", "badge_v1.png")
    render(path=p)
    print("saved", p)
