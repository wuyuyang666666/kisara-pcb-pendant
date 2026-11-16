# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章（PCB 挂件）正式设计 v3
源：AI 改绘的黑白线稿（1024²）
板框：Φ56 圆 + 顶部半圆挂耳 Φ3 孔
图层：黑阻焊 + 白丝印线稿 + 沉金眼睛 / 外圈
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import lineart as LA
import contour as C

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Convert_this_anime_illustratio_2026-11-05T15-01-23.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
SILK_W = 0.20
RING_R = 26.0
RING_W = 0.26

# 线稿像素框（1024²）
EYE_BOXES = [(294, 422, 397, 531), (623, 384, 716, 515)]
SRC_W = SRC_H = 1024


# ---------------------------------------------------------------- 板框

def board_outline(n_arc=240):
    R = D_BOARD / 2
    hw = TAB_W / 2.0
    y_j = math.sqrt(R * R - hw * hw)
    cap_cy = R + TAB_H - hw
    a0 = math.atan2(y_j, -hw)
    a1 = math.atan2(y_j, hw) + 2 * math.pi
    pts = [(R * math.cos(a0 + (a1 - a0) * i / n_arc),
            R * math.sin(a0 + (a1 - a0) * i / n_arc)) for i in range(n_arc + 1)]
    for i in range(25):
        a = -math.pi / 2 + math.pi * i / 24
        pts.append((hw * math.cos(a), cap_cy + hw * math.sin(a)))
    return pts


def hole_center():
    return (0.0, D_BOARD / 2 + TAB_H - TAB_W / 2.0)


# ---------------------------------------------------------------- 映射

SCALE = D_BOARD / max(SRC_W, SRC_H)


def mp(px, py):
    return ((px - SRC_W / 2) * SCALE, (SRC_H / 2 - py) * SCALE)


def mm_to_px(mx, my):
    return (mx / SCALE + SRC_W / 2, SRC_H / 2 - my / SCALE)


# ---------------------------------------------------------------- 线稿

def load_mask():
    a = np.asarray(Image.open(LIN).convert("L"), np.float32)
    return a < 128


def silk_paths(mask, min_len=12, eps=0.7, skip_eyes=True):
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    mx, my = mp(xx + 0.5, yy + 0.5)
    r = D_BOARD / 2 - 0.30
    m = mask & (mx * mx + my * my < r * r)

    paths = LA.trace(LA.thin(m), min_len=min_len)
    paths = [[(float(x), float(y)) for (y, x) in p] for p in paths]
    paths = [LA.rdp(LA.smooth(p, 1), eps) for p in paths]

    out = []
    for p in paths:
        if len(p) < 2:
            continue
        pts = [mp(x, y) for x, y in p]
        if skip_eyes:
            cx = sum(q[0] for q in pts) / len(pts)
            cy = sum(q[1] for q in pts) / len(pts)
            if inside_any_eye(cx, cy):
                continue
        out.append(pts)
    return out


# ---------------------------------------------------------------- 眼睛

EYE_POLY = []          # 由 build_eyes 填充


def inside_any_eye(mx, my, grow=0.35):
    for poly in EYE_POLY:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        if (min(xs) - grow <= mx <= max(xs) + grow and
                min(ys) - grow <= my <= max(ys) + grow):
            return True
    return False


def build_eyes(mask):
    """
    眼睛内部：线稿里被黑线围住的白色区域（巩膜 + 虹膜 + 高光），
    做闭运算吞掉内部的细线，得到一个实心杏仁 -> 沉金开窗
    """
    white = Image.fromarray((~mask).astype(np.uint8) * 255, "L")
    eyes = []
    for x0, y0, x1, y1 in EYE_BOXES:
        sub = np.zeros_like(mask, bool)
        sub[y0:y1, x0:x1] = True
        reg = (~mask) & sub
        img = Image.fromarray(reg.astype(np.uint8) * 255, "L")
        img = img.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(11))
        img = img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        rings = C.extract(img)
        if not rings:
            continue
        ring = max(rings, key=lambda r: abs(C.ring_area(r)))
        pts = LA.rdp([mp(x, y) for x, y in ring], 0.12)
        if len(pts) >= 3:
            eyes.append(pts)
    return eyes


def catchlights(eyes):
    """眼中高光：白丝印小点，放在瞳孔左上"""
    out = []
    for poly in eyes:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        cx = (min(xs) + max(xs)) / 2 - (max(xs) - min(xs)) * 0.20
        cy = (min(ys) + max(ys)) / 2 + (max(ys) - min(ys)) * 0.22
        r = 0.42
        out.append([(cx + r * math.cos(2 * math.pi * i / 20),
                     cy + r * math.sin(2 * math.pi * i / 20)) for i in range(20)])
    return out


# ---------------------------------------------------------------- 组装

def build():
    global EYE_POLY
    mask = load_mask()
    eyes = build_eyes(mask)
    EYE_POLY = eyes
    silk = silk_paths(mask)

    ring = [(RING_R * math.cos(2 * math.pi * i / 240),
             RING_R * math.sin(2 * math.pi * i / 240)) for i in range(240)]

    return {
        "outline": board_outline(),
        "hole": hole_center() + (HOLE_D,),
        "silk": [(p, SILK_W) for p in silk],
        "gold_fill": eyes,
        "gold_stroke": [(ring, RING_W)],
        "mask_clear": [],
        "silk_fill": catchlights(eyes),
        "size_mm": (D_BOARD, D_BOARD + TAB_H),
    }


if __name__ == "__main__":
    d = build()
    print("丝印", len(d["silk"]), "金块", len(d["gold_fill"]))
    for g in d["gold_fill"]:
        xs = [p[0] for p in g]; ys = [p[1] for p in g]
        print("  eye x %.1f..%.1f  y %.1f..%.1f" % (min(xs), max(xs), min(ys), max(ys)))
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "medallion.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
