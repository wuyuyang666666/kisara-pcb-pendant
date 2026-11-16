# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章（PCB 挂件）v4
思路：位图分区，而不是描线。
  · 线稿的黑 = 不印（露出黑色阻焊）
  · 角色内部的空白 = 白丝印（脸、头发、手）
  · 眼睛 = 沉金开窗
板框 Φ56 + 顶部挂耳 Φ3 孔
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import contour as C
import lineart as LA

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Convert_this_anime_illustratio_2026-11-05T15-01-23.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
RING_R = 25.9
RING_W = 0.0            # 0 = 不画金环

EYE_SEEDS = [(346, 476), (668, 450)]     # (x, y) 眼白内的种子点
EYE_BOXES = [(280, 400, 410, 545), (610, 370, 735, 520)]
SRC_W = SRC_H = 1024
SCALE = D_BOARD / 1024.0


# ---------------------------------------------------------------- 位图工具

def dilate(m, k):
    im = Image.fromarray(m.astype(np.uint8) * 255, "L")
    return np.asarray(im.filter(ImageFilter.MaxFilter(k))) > 127


def erode(m, k):
    im = Image.fromarray(m.astype(np.uint8) * 255, "L")
    return np.asarray(im.filter(ImageFilter.MinFilter(k))) > 127


def close(m, k):
    return erode(dilate(m, k), k)


def flood(img_L, seed, value):
    """在 L 图上从 seed 泛洪填充为 value，返回新图"""
    im = img_L.copy()
    ImageDraw.floodfill(im, seed, value, thresh=8)
    return im


def board_circle_mask(px_per_mm=None, margin=0.30):
    h, w = SRC_H, SRC_W
    yy, xx = np.mgrid[0:h, 0:w]
    mx = (xx + 0.5 - SRC_W / 2) * SCALE
    my = (SRC_H / 2 - (yy + 0.5)) * SCALE
    r = D_BOARD / 2 - margin
    return mx * mx + my * my < r * r


# ---------------------------------------------------------------- 分区

def segments():
    line = np.asarray(Image.open(LIN).convert("L"), np.float32) < 128
    white = ~line
    wi = Image.fromarray(white.astype(np.uint8) * 255, "L")

    # 外部背景：从四角泛洪
    bg_img = wi.copy()
    for seed in [(0, 0), (SRC_W - 1, 0), (0, SRC_H - 1), (SRC_W - 1, SRC_H - 1)]:
        ImageDraw.floodfill(bg_img, seed, 128, thresh=8)
    bg = np.asarray(bg_img) == 128
    char = ~bg                       # 角色（含线稿黑）
    inside = char & white            # 角色内部的“纸”

    # 眼睛：从眼白种子泛洪后闭运算吞掉虹膜线
    eyes = np.zeros_like(line)
    for (sx, sy), box in zip(EYE_SEEDS, EYE_BOXES):
        sub = wi.copy()
        ImageDraw.floodfill(sub, (sx, sy), 200, thresh=8)
        m = np.asarray(sub) == 200
        m = close(m, 9)
        x0, y0, x1, y1 = box
        bm = np.zeros_like(m)
        bm[y0:y1, x0:x1] = True
        m = m & bm & inside
        eyes |= m

    silk = inside & ~eyes
    return line, inside, eyes, silk, char


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


def mp(px, py):
    return ((px - SRC_W / 2) * SCALE, (SRC_H / 2 - py) * SCALE)


# ---------------------------------------------------------------- 位图 -> 多边形

def rings_of(mask, clip=True, eps=0.15, min_area_px=12):
    m = mask & (board_circle_mask() if clip else np.ones_like(mask))
    img = Image.fromarray(m.astype(np.uint8) * 255, "L")
    rings = C.extract(img)
    out = []
    for r in rings:
        if abs(C.ring_area(r)) < min_area_px:
            continue
        pts = [mp(x, y) for x, y in r]
        pts = LA.rdp(pts, eps)
        if len(pts) >= 3:
            out.append(pts)
    return out


# ---------------------------------------------------------------- 预览

BG = (206, 204, 198)
MASK = (20, 20, 23)
GOLD = (198, 157, 78)
GOLD_HI = (240, 212, 156)
SILK = (241, 241, 237)


def preview(silk_m, gold_m, ppm=16, path=None):
    W = int((D_BOARD + 18) * ppm)
    H = int((D_BOARD + TAB_H + 20) * ppm)
    cx, cy = W / 2, H - (D_BOARD / 2 + 10) * ppm

    def T(x, y):
        return (cx + x * ppm, cy - y * ppm)

    img = Image.new("RGB", (W, H), BG)
    poly = [T(*p) for p in board_outline()]
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon(poly, fill=255)
    sh = bm.filter(ImageFilter.GaussianBlur(ppm * 0.5))
    img = Image.composite(Image.new("RGB", (W, H), (152, 150, 144)), img,
                          sh.point(lambda v: int(v * 0.45)))

    layer = Image.new("RGB", (W, H), MASK)

    nonlocal_layer = layer
    for m, color in ((gold_m, GOLD), (silk_m, SILK)):
        im = Image.fromarray(m.astype(np.uint8) * 255, "L")
        size = int(round(D_BOARD * ppm))
        im = im.resize((size, size), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
        msk = Image.new("L", (W, H), 0)
        msk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
        nonlocal_layer = Image.composite(Image.new("RGB", (W, H), color), nonlocal_layer, msk)

    img = Image.composite(nonlocal_layer, img, bm)

    # 金高光
    im = Image.fromarray(gold_m.astype(np.uint8) * 255, "L")
    size = int(round(D_BOARD * ppm))
    im = im.resize((size, size), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
    gmask = Image.new("L", (W, H), 0)
    gmask.paste(im, (int(cx - size / 2), int(cy - size / 2)))
    gmask = gmask.filter(ImageFilter.GaussianBlur(ppm * 0.12))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gmask.point(lambda v: int(v * 0.40)))

    hx, hy, hd = hole_center() + (HOLE_D,)
    r = hd / 2 * ppm
    dd = ImageDraw.Draw(img)
    dd.ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                cx + hx * ppm + r, cy - hy * ppm + r], fill=BG)
    if path:
        img.save(path)
    return img


def main():
    line, inside, eyes, silk, char = segments()
    print("inside %.3f  eyes %.4f  silk %.3f  char %.3f"
          % (inside.mean(), eyes.mean(), silk.mean(), char.mean()))
    preview(silk, eyes, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v4.png"))
    print("saved")


if __name__ == "__main__":
    main()
