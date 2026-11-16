#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成品效果模拟：哑黑阻焊 + 沉金 + 白色丝印
几何来自 build/kisara_outline.json（板框）与 artwork.py（L1 图案）
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFilter

import artwork as A

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
JSON = os.path.join(ROOT, "build", "kisara_outline.json")

PPM = 16
BLACK = (22, 22, 24)
BLACK_LT = (34, 34, 37)
GOLD = (206, 168, 98)
GOLD_HI = (238, 208, 150)
SILK = (242, 242, 240)


def ell(cx, cy, rx, ry, n=48):
    return A.ell(cx, cy, rx, ry, n)


def make_bg(size):
    img = Image.new("RGB", size, (233, 231, 226))
    d = ImageDraw.Draw(img)
    for i in range(0, size[1], 2):
        c = 229 + int(5 * math.sin(i / 43.0) + 3 * math.sin(i / 11.0))
        d.line([(0, i), (size[0], i)], fill=(c, c - 2, c - 7))
    return img


def render(out_json=JSON, path=None, ppm=PPM):
    d = json.load(open(out_json, encoding="utf-8"))
    W, H = d["size_mm"]
    poly = d["outline"]
    hole = d["mount_hole"]

    pad = 34
    size = (int(W * ppm) + pad * 2, int(H * ppm) + pad * 2)

    def T(pts):
        return [(pad + x * ppm, size[1] - pad - y * ppm) for x, y in pts]

    base = make_bg(size)

    board = Image.new("L", size, 0)
    bd = ImageDraw.Draw(board)
    bd.polygon(T(poly), fill=255)
    bd.polygon(T(ell(hole["cx"], hole["cy"], hole["d"] / 2, hole["d"] / 2, 48)), fill=0)

    # 投影
    shadow = board.filter(ImageFilter.GaussianBlur(7))
    shadow = shadow.point(lambda v: int(v * 0.30))
    base = Image.composite(Image.new("RGB", size, (146, 143, 136)), base, shadow)

    # 板身
    base = Image.composite(Image.new("RGB", size, BLACK), base, board)

    # 板面细微质感（哑光黑）
    tex = Image.new("RGB", size, BLACK)
    td = ImageDraw.Draw(tex)
    for i in range(0, size[1], 4):
        td.line([(0, i), (size[0], i)], fill=BLACK_LT)
    tex = tex.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.composite(tex, base, board.point(lambda v: int(v * 0.45)))

    # ---------------- 图案层（按 artwork 数组顺序叠加） ----------------
    items = A.build(cx=d.get("axis_x", 27.65))
    KIND_COLOR = {"gold": GOLD, "black": BLACK, "silk": SILK}
    for it in items:
        if len(it["pts"]) < 3:
            continue
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).polygon(T(it["pts"]), fill=255)
        m = Image.composite(m, Image.new("L", size, 0), board)
        base = Image.composite(Image.new("RGB", size, KIND_COLOR[it["kind"]]), base, m)

    # 沉金高光（左上方向的一点反光）
    gm = Image.new("L", size, 0)
    gd = ImageDraw.Draw(gm)
    for it in items:
        if it["kind"] == "gold" and len(it["pts"]) >= 3:
            gd.polygon(T(it["pts"]), fill=255)
    gm = Image.composite(gm, Image.new("L", size, 0), board)
    gm = gm.filter(ImageFilter.GaussianBlur(1.4))
    gm = gm.point(lambda v: int(v * 0.30))
    base = Image.composite(Image.new("RGB", size, GOLD_HI), base, gm)

    # 铣边倒角
    ImageDraw.Draw(base).line(T(poly) + [T(poly)[0]], fill=(66, 66, 70), width=2, joint="curve")

    if path:
        base.save(path)
    return base


if __name__ == "__main__":
    p = os.path.join(ROOT, "assets", "effect_v2.png")
    render(path=p)
    print("saved", p)
