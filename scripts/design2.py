# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章（PCB 挂件）正式设计
板框：Φ56 圆 + 顶部半圆挂耳（Φ3 孔）
图层：黑阻焊底 + 白丝印线稿 + 沉金开窗（眼睛 / 发夹 / 外圈）
所有几何统一成 mm，原点在圆心，输出给渲染器与 Gerber 生成器共用。
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import lineart as LA
import contour as C

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
SRC = r"C:\Users\rain\.workbuddy\clipboard-images\clipboard-2026-11-05T13-05-43-527Z-c930b2e8.jpg"

D_BOARD = 56.0
CROP = (110, 0, 950, 840)
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0

SILK_W = 0.20          # 丝印线宽
RING_R = 26.1          # 金色外圈半径
RING_W = 0.28


# ---------------------------------------------------------------- 板框

def board_outline(n_arc=240):
    R = D_BOARD / 2
    hw = TAB_W / 2.0
    y_j = math.sqrt(R * R - hw * hw)
    cap_cy = R + TAB_H - hw
    a0 = math.atan2(y_j, -hw)
    a1 = math.atan2(y_j, hw) + 2 * math.pi
    pts = []
    for i in range(n_arc + 1):
        a = a0 + (a1 - a0) * i / n_arc
        pts.append((R * math.cos(a), R * math.sin(a)))
    for i in range(25):
        a = -math.pi / 2 + math.pi * i / 24
        pts.append((hw * math.cos(a), cap_cy + hw * math.sin(a)))
    return pts


def hole_center():
    return (0.0, D_BOARD / 2 + TAB_H - TAB_W / 2.0)


# ---------------------------------------------------------------- 映射

def mapper():
    x0, y0, x1, y1 = CROP
    w, h = x1 - x0, y1 - y0
    s = D_BOARD / max(w, h)
    return (lambda px, py: ((px - x0 - w / 2) * s, (h / 2 - (py - y0)) * s)), s


# ---------------------------------------------------------------- 线稿

def line_paths(crop, t=24, k=13, min_area=24, min_len=8, eps=0.8):
    from PIL import ImageFilter as IF
    mask, bh = LA.line_mask(crop, t=t, k=k)
    mimg = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    mimg = mimg.filter(IF.MaxFilter(3)).filter(IF.MinFilter(3))
    mask = np.asarray(mimg) > 127
    mask = LA.drop_small(mask, min_area)

    mp, s = mapper()
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    mx, my = mp(xx + 0.5, yy + 0.5)
    r = D_BOARD / 2 - 0.30
    mask = mask & (mx * mx + my * my < r * r)

    paths = LA.trace(LA.thin(mask), min_len=min_len)
    paths = [[(float(x), float(y)) for (y, x) in p] for p in paths]
    paths = [LA.rdp(LA.smooth(p, 1), eps) for p in paths]
    return [[mp(x, y) for x, y in p] for p in paths if len(p) >= 2]


# ---------------------------------------------------------------- 沉金块（眼睛 / 发夹）

def blob_polys(crop, thr=70, min_px=900, max_n=3, erode=1):
    """从暗部取实心块，返回 [(多边形mm, 面积mm2, 像素bbox)]"""
    L = LA.to_l(crop)
    m = (L < thr).astype(np.uint8) * 255
    img = Image.fromarray(m, "L")
    if erode:
        img = img.filter(ImageFilter.MinFilter(2 * erode + 1))
    rings = C.extract(img)
    mp, s = mapper()
    out = []
    for r in rings:
        area_px = abs(C.ring_area(r))
        if area_px < min_px:
            continue
        pts = LA.rdp([mp(x, y) for x, y in r], 0.18)
        if len(pts) < 3:
            continue
        xs = [p[0] for p in r]
        ys = [p[1] for p in r]
        out.append((pts, area_px, (min(xs), min(ys), max(xs), max(ys))))
    out.sort(key=lambda t: -t[1])
    return out[:max_n]


def pupil_px(crop, box, thr=42):
    """在像素框内找瞳孔（最暗区），返回 (cx, cy, r_px) 像素坐标"""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(crop.width, x1), min(crop.height, y1)
    if x1 - x0 < 6 or y1 - y0 < 6:
        return None
    L = LA.to_l(crop)
    sub = L[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub < thr)
    if len(xs) < 40:
        return None
    return (xs.mean() + x0, ys.mean() + y0,
            math.sqrt(len(xs) / math.pi))


def eye_gold(crop):
    """两只眼睛：暗块多边形（金）+ 瞳孔圆孔（清空）"""
    mp, s = mapper()
    blobs = blob_polys(crop, thr=70, min_px=2500, max_n=8, erode=1)
    eyes = []
    for pts, area, bb in blobs:
        w = (max(p[0] for p in pts) - min(p[0] for p in pts))
        h = (max(p[1] for p in pts) - min(p[1] for p in pts))
        if 5.0 < w < 12.0 and 5.0 < h < 13.0:
            eyes.append((pts, bb))
        if len(eyes) == 2:
            break
    res = []
    for pts, bb in eyes:
        p = pupil_px(crop, bb, thr=42)
        hole = None
        if p:
            hx, hy = mp(p[0], p[1])
            rr = p[2] * s * 0.80
            hole = [(hx + rr * math.cos(2 * math.pi * i / 30),
                     hy + rr * math.sin(2 * math.pi * i / 30)) for i in range(30)]
        res.append({"gold": pts, "clear": hole})
    return res


# ---------------------------------------------------------------- 组装

def build(t=24, k=13):
    crop = Image.open(SRC).convert("RGB").crop(CROP)
    silk = line_paths(crop, t=t, k=k)
    eyes = eye_gold(crop)

    R = RING_R
    ring = [(R * math.cos(2 * math.pi * i / 240),
             R * math.sin(2 * math.pi * i / 240)) for i in range(240)]

    # 眼中高光（白点）：放在瞳孔左上，直径 0.7mm
    catch = []
    for e in eyes:
        if e["clear"] is None:
            continue
        cx = sum(p[0] for p in e["clear"]) / len(e["clear"])
        cy = sum(p[1] for p in e["clear"]) / len(e["clear"])
        r = 0.36
        catch.append([(cx - 0.55 + r * math.cos(2 * math.pi * i / 16),
                       cy + 0.55 + r * math.sin(2 * math.pi * i / 16))
                      for i in range(16)])

    return {
        "outline": board_outline(),
        "hole": hole_center() + (HOLE_D,),
        "silk": [(p, SILK_W) for p in silk],
        "gold_fill": [e["gold"] for e in eyes],
        "gold_stroke": [(ring, RING_W)],
        "mask_clear": [e["clear"] for e in eyes if e["clear"]],
        "silk_fill": catch,
        "size_mm": (D_BOARD, D_BOARD + TAB_H),
    }


def dump(path, d):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    d = build()
    print("丝印线", len(d["silk"]), "金块", len(d["gold_fill"]),
          "清空", len(d["mask_clear"]))
    dump(os.path.join(ROOT, "build", "medallion.json"), d)
    print("saved json")
