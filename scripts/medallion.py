# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章（PCB 挂件）
板框：Φ56 圆 + 顶部挂耳（Φ3 孔）
图案：原图线稿 -> 白丝印描线；眼睛虹膜 / X 发夹 / 外圈 -> 沉金开窗
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import lineart as LA

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
SRC = r"C:\Users\rain\.workbuddy\clipboard-images\clipboard-2026-11-05T13-05-43-527Z-c930b2e8.jpg"

D_BOARD = 56.0
CROP = (110, 0, 950, 840)          # 头像区
TAB_W, TAB_H, TAB_R = 11.0, 7.5, 4.2
HOLE_D = 3.0

GOLD = (198, 156, 78)
SILK = (238, 238, 234)
BLACK = (26, 26, 28)


# ---------------------------------------------------------------- 板框

def board_outline(n_arc=200):
    """Φ56 圆 + 顶部半圆挂耳，逆时针闭合多边形（mm，原点在圆心）"""
    R = D_BOARD / 2
    hw = TAB_W / 2.0
    y_j = math.sqrt(R * R - hw * hw)        # 圆与挂耳侧边的交点高度
    cap_cy = R + TAB_H - hw                 # 挂耳顶部半圆圆心
    a0 = math.atan2(y_j, -hw)               # 左交点角度
    a1 = math.atan2(y_j, hw) + 2 * math.pi  # 绕一圈到右交点
    pts = []
    for i in range(n_arc + 1):
        a = a0 + (a1 - a0) * i / n_arc
        pts.append((R * math.cos(a), R * math.sin(a)))
    # 右交点 -> 挂耳顶部半圆 -> 左交点
    steps = 24
    for i in range(steps + 1):
        a = -math.pi / 2 + math.pi * i / steps
        pts.append((hw * math.cos(a), cap_cy + hw * math.sin(a)))
    return pts


def hole_center():
    return (0.0, D_BOARD / 2 + TAB_H - TAB_W / 2.0)


# ---------------------------------------------------------------- 坐标映射

def make_mapper():
    x0, y0, x1, y1 = CROP
    w, h = x1 - x0, y1 - y0
    s = D_BOARD / max(w, h)
    return lambda px, py: ((px - x0 - w / 2) * s, (h / 2 - (py - y0)) * s), s


def artwork(crop_img, t=24, k=13, min_area=24, min_len=8, eps=0.8,
            clip_r=None):
    """
    线稿 -> 板坐标折线。
    clip_r: 只保留落在半径 clip_r 内的像素（板外的一律丢掉，
            否则背景竖条会跑到圆外面）
    """
    from PIL import ImageFilter
    mask, bh = LA.line_mask(crop_img, t=t, k=k)
    # 桥接 1px 断口，让发丝线连续
    mimg = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    mimg = mimg.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(mimg) > 127
    mask = LA.drop_small(mask, min_area)

    if clip_r is not None:
        mp0, s0 = make_mapper()
        h, w = mask.shape
        yy, xx = np.mgrid[0:h, 0:w]
        mx, my = mp0(xx + 0.5, yy + 0.5)
        mask = mask & (mx * mx + my * my < clip_r * clip_r)

    skel = LA.thin(mask)
    paths = LA.trace(skel, min_len=min_len)
    # trace 内部是 (row, col)，统一成 (x, y)
    paths = [[(float(x), float(y)) for (y, x) in p] for p in paths]
    paths = [LA.rdp(LA.smooth(p, 1), eps) for p in paths]
    paths = [p for p in paths if len(p) >= 2]

    mp, s = make_mapper()
    out = [[mp(x, y) for x, y in pl] for pl in paths]
    return out, s, mask, skel


# ---------------------------------------------------------------- 渲染

def render(silk_paths, path_png, ppm=12, board=None, show_hole=True,
           gold=None, fit=None):
    W = int((D_BOARD + 16) * ppm)
    H = int((D_BOARD + 20) * ppm)
    bg = Image.new("RGB", (W, H), (206, 204, 198))
    cx, cy = W / 2, H / 2 + 4 * ppm

    def T(x, y):
        return (cx + x * ppm, cy - y * ppm)

    poly = board or board_outline()
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon([T(*p) for p in poly], fill=255)

    layer = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(layer)

    if gold:
        for g in gold:
            d.polygon([T(*p) for p in g], fill=GOLD)

    lw = max(1, int(round(0.22 * ppm)))
    for pl in silk_paths:
        if len(pl) < 2:
            continue
        d.line([T(*p) for p in pl], fill=SILK, width=lw, joint="curve")

    img = Image.composite(layer, bg, bm)

    if show_hole:
        hx, hy = hole_center()
        r = HOLE_D / 2 * ppm
        dd = ImageDraw.Draw(img)
        dd.ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                    cx + hx * ppm + r, cy - hy * ppm + r],
                   fill=(206, 204, 198), outline=(120, 118, 112))
        # 孔周围一圈金色沉金环
        if gold is not None:
            pass

    if fit:
        img = img.crop(fit)
    img.save(path_png)
    return img


def main():
    src = Image.open(SRC).convert("RGB")
    crop = src.crop(CROP)
    R = D_BOARD / 2
    paths, s, mask, skel = artwork(crop, clip_r=R - 0.35)
    print("线稿折线", len(paths), " 比例 mm/px =", round(s, 5),
          " 骨架像素", int(skel.sum()))
    render(paths, os.path.join(ROOT, "assets", "medallion_v1.png"), ppm=14)
    print("saved")


if __name__ == "__main__":
    main()
