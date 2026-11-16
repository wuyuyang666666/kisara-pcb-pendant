#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预览渲染：模拟哑黑阻焊 + 沉金 + 白色丝印的实际观感"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import math
from PIL import Image, ImageDraw, ImageFont
import design as D

S = 12  # px per mm
MARGIN = 30

BOARD_BLACK = (26, 26, 28)
GOLD = (212, 175, 105)
GOLD_HI = (240, 214, 160)
SILK = (238, 238, 238)
BG = (232, 232, 232)


def mk(w_mm, h_mm, extra=0):
    img = Image.new("RGB", (int(w_mm * S) + MARGIN * 2, int(h_mm * S) + MARGIN * 2 + extra), BG)
    return img


def T(pts, h_mm):
    """mm -> px（y 翻转）"""
    return [(MARGIN + x * S, MARGIN + (h_mm - y) * S) for x, y in pts]


def render(outline, layers, size_mm, title="", path=None):
    """layers: [(polygon_pts, color), ...] 按顺序绘制在板框内"""
    w, h = size_mm
    img = mk(w, h, extra=26)
    d = ImageDraw.Draw(img)
    H = h

    op = T(outline, H)
    d.polygon(op, fill=BOARD_BLACK)
    d.line(op + [op[0]], fill=(70, 70, 70), width=2)

    for pts, color in layers:
        if len(pts) > 2:
            d.polygon(T(pts, H), fill=color)

    d.text((6, 6), title, fill=(20, 20, 20))
    if path:
        img.save(path)
    return img


def build(version="A"):
    out = D.board_outline()
    layers = []
    # 脸部（沉金）
    layers.append((D.face_ellipse(), GOLD))
    eL, eR = D.eyes()
    layers.append((eL, BOARD_BLACK))
    layers.append((eR, BOARD_BLACK))
    # 挂孔
    cx, cy, r = D.MOUNT_HOLE
    layers.append((D.poly_ellipse(cx, cy, r, r, 32), (240, 240, 240)))
    return out, layers


if __name__ == "__main__":
    out, layers = build()
    bb = D.bbox(out)
    print("bbox", [round(v, 2) for v in bb])
    w_mm, h_mm = bb[2] - bb[0], bb[3] - bb[1]
    print(f"size {w_mm:.1f} x {h_mm:.1f} mm")
    p = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\preview_outline.png"
    render(out, layers, (bb[2], bb[3]), "Kisara pendant - outline v1", p)
    print("saved", p)
