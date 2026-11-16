# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章（PCB 挂件）最终版
源：AI 改绘的黑白线稿
  白丝印 = 圆内除线稿外全部（脸、头发、手）
  黑     = 线稿本身（不印，露出黑色阻焊）+ 板外
  沉金   = 两只眼睛（挖掉瞳孔）
板框 Φ56 圆 + 顶部半圆挂耳 Φ3 孔
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import bmp
import edge as E
import lineart as LA

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Convert_this_anime_illustratio_2026-11-05T15-01-23.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
EDGE_MARGIN = 0.35          # 丝印离板边距离

EYE_BOXES = [(280, 400, 410, 545), (610, 370, 735, 520)]
SRC = 1024
SCALE = D_BOARD / SRC

BG = (206, 204, 198)
MASK_C = (20, 20, 23)
GOLD = (198, 157, 78)
GOLD_HI = (240, 212, 156)
SILK = (241, 241, 237)


# ---------------------------------------------------------------- 板框

def board_outline(n_arc=260):
    R = D_BOARD / 2
    hw = TAB_W / 2.0
    y_j = math.sqrt(R * R - hw * hw)
    cap_cy = R + TAB_H - hw
    a0 = math.atan2(y_j, -hw)
    a1 = math.atan2(y_j, hw) + 2 * math.pi
    pts = [(R * math.cos(a0 + (a1 - a0) * i / n_arc),
            R * math.sin(a0 + (a1 - a0) * i / n_arc)) for i in range(n_arc + 1)]
    # 从右交点竖直上去，绕顶部半圆，再竖直下来回到左交点
    pts.append((hw, cap_cy))
    for i in range(1, 25):
        a = math.pi * i / 24
        pts.append((hw * math.cos(a), cap_cy + hw * math.sin(a)))
    pts.append((-hw, cap_cy))
    pts.append((-hw, y_j))
    return pts


def hole():
    return (0.0, D_BOARD / 2 + TAB_H - TAB_W / 2.0, HOLE_D)


def mp(px, py):
    return ((px - SRC / 2) * SCALE, (SRC / 2 - py) * SCALE)


def circle_mask(margin=EDGE_MARGIN):
    yy, xx = np.mgrid[0:SRC, 0:SRC]
    mx = (xx + 0.5 - SRC / 2) * SCALE
    my = (SRC / 2 - (yy + 0.5)) * SCALE
    r = D_BOARD / 2 - margin
    return mx * mx + my * my < r * r


# ---------------------------------------------------------------- 图层

def build_masks():
    line = np.asarray(Image.open(LIN).convert("L"), np.float32) < 128
    white = ~line
    circ = circle_mask()

    gold = np.zeros_like(line)
    pupil = np.zeros_like(line)
    for x0, y0, x1, y1 in EYE_BOXES:
        sub = np.zeros_like(line)
        sub[y0:y1, x0:x1] = True
        comps = bmp.components(white & sub, min_area=60)
        # 眼睛：完全落在框内、面积最大的连通块
        eye = None
        for a, r in comps:
            ys, xs = np.nonzero(r)
            if xs.min() > x0 + 1 and xs.max() < x1 - 1 and \
               ys.min() > y0 + 1 and ys.max() < y1 - 1:
                eye = (a, r)
                break
        if eye is None:
            continue
        a_eye, eye_r = eye
        ys, xs = np.nonzero(eye_r)
        ex0, ex1, ey0, ey1 = xs.min(), xs.max(), ys.min(), ys.max()
        # 用椭圆拟合眼睛外框：形状规整、左右一致，也便于制造
        em = Image.new("L", (SRC, SRC), 0)
        ImageDraw.Draw(em).ellipse([ex0 + 1, ey0 + 1, ex1 - 1, ey1 - 1], fill=255)
        gold |= np.asarray(em) > 127
        # 瞳孔：落在眼内、面积占比 3%~25% 的块
        for a, r in comps[1:]:
            ys2, xs2 = np.nonzero(r)
            cx, cy = xs2.mean(), ys2.mean()
            if not (ex0 < cx < ex1 and ey0 < cy < ey1):
                continue
            if 0.03 * a_eye < a < 0.25 * a_eye:
                pupil |= r

    gold = bmp.close(gold | pupil, 3)
    silk = white & circ & ~gold
    return {
        "silk": silk,
        "gold": gold & circ,
        "clear": pupil & gold,
        "line": line,
    }


# ---------------------------------------------------------------- 位图 -> 多边形

def rings_of(mask, eps=0.05, min_area_px=15):
    out = []
    for r in E.rings(mask):
        if abs(E.area(r)) < min_area_px:
            continue
        pts = LA.rdp([mp(x, y) for x, y in r], eps)
        if len(pts) >= 3:
            out.append(pts)
    return out


# ---------------------------------------------------------------- 预览

def preview(masks, ppm=16, path=None):
    W = int((D_BOARD + 18) * ppm)
    H = int((D_BOARD + TAB_H + 20) * ppm)
    cx, cy = W / 2, H - (D_BOARD / 2 + 10) * ppm

    def T(x, y):
        return (cx + x * ppm, cy - y * ppm)

    img = Image.new("RGB", (W, H), BG)
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon([T(*p) for p in board_outline()], fill=255)
    sh = bm.filter(ImageFilter.GaussianBlur(ppm * 0.5))
    img = Image.composite(Image.new("RGB", (W, H), (152, 150, 144)), img,
                          sh.point(lambda v: int(v * 0.45)))

    size = int(round(D_BOARD * ppm))

    def to_board(m, thr=110):
        im = Image.fromarray(m.astype(np.uint8) * 255, "L")
        im = im.resize((size, size), Image.LANCZOS).point(lambda v: 255 if v > thr else 0)
        full = Image.new("L", (W, H), 0)
        full.paste(im, (int(cx - size / 2), int(cy - size / 2)))
        return full

    layer = Image.new("RGB", (W, H), MASK_C)
    for key, color in (("gold", GOLD), ("clear", MASK_C), ("silk", SILK)):
        mk = to_board(masks[key])
        layer = Image.composite(Image.new("RGB", (W, H), color), layer, mk)

    img = Image.composite(layer, img, bm)

    gm = to_board(masks["gold"]).filter(ImageFilter.GaussianBlur(ppm * 0.12))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.point(lambda v: int(v * 0.42)))

    hx, hy, hd = hole()
    r = hd / 2 * ppm
    dd = ImageDraw.Draw(img)
    dd.ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                cx + hx * ppm + r, cy - hy * ppm + r], fill=BG)
    if path:
        img.save(path)
    return img


def main():
    m = build_masks()
    print("silk %.3f  gold %.4f  clear %.5f"
          % (m["silk"].mean(), m["gold"].mean(), m["clear"].mean()))
    preview(m, ppm=18, path=os.path.join(ROOT, "assets", "medallion_v5.png"))
    print("saved")


if __name__ == "__main__":
    main()
