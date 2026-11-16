#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
位图三色分离：把立绘转成「黑阻焊 / 沉金 / 白丝印」三层区域

原理：灰度分层 + marching squares。PCB 只有三种"墨水"，所以本质上是三色版画。
输出：{'gold': [ring...], 'silk': [ring...]}  ring 为 mm 坐标闭合多边形
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageFilter

import contour as C


def prep(src, target_px=420, crop="square"):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if crop == "square":
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    im = im.resize((target_px, target_px), Image.LANCZOS)
    return im.convert("L")


def layer_mask(gray, lo, hi=None):
    """返回某灰度区间的二值图（255=命中）"""
    px = gray.load()
    w, h = gray.size
    out = Image.new("L", (w, h), 0)
    po = out.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if hi is None:
                ok = v >= lo
            else:
                ok = lo <= v < hi
            if ok:
                po[x, y] = 255
    return out


def clean(mask, min_px=40):
    """去掉过小的连通块，避免产生不可制造的小碎铜"""
    w, h = mask.size
    px = mask.load()
    from collections import deque
    seen = bytearray(w * h)
    out = Image.new("L", (w, h), 0)
    po = out.load()
    for y in range(h):
        for x in range(w):
            if px[x, y] == 0 or seen[y * w + x]:
                continue
            comp = []
            q = deque([(x, y)])
            seen[y * w + x] = 1
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and px[nx, ny]:
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            if len(comp) >= min_px:
                for cx, cy in comp:
                    po[cx, cy] = 255
    return out


def rings_to_mm(rings, box_px, target_mm, ox=0.0, oy=0.0, min_area_mm2=0.7):
    """像素环 -> mm 多边形，过滤小面积"""
    n = box_px
    k = target_mm / n
    out = []
    for r in rings:
        mm = [(x * k + ox, (n - y) * k + oy) for x, y in r]
        a = abs(C.ring_area(mm))
        if a < min_area_mm2:
            continue
        out.append((a, mm))
    out.sort(key=lambda t: -t[0])
    return [p for _, p in out]


def separate(src, target_mm=54.0, target_px=420,
             dark_max=96, light_min=205, smooth=1):
    gray = prep(src, target_px)
    if smooth:
        gray = gray.filter(ImageFilter.MedianFilter(3))

    dark = clean(layer_mask(gray, 0, dark_max), min_px=30)        # 黑（头发、衣服暗部）
    light = clean(layer_mask(gray, light_min), min_px=30)         # 白（高光、皮肤亮部）

    rings_d = C.extract(dark)
    rings_l = C.extract(light)

    gold = rings_to_mm(rings_d, target_px, target_mm)
    silk = rings_to_mm(rings_l, target_px, target_mm)
    return gold, silk, gray


if __name__ == "__main__":
    SRC = r"C:\Users\rain\.workbuddy\clipboard-images\clipboard-2026-11-05T13-05-43-527Z-c930b2e8.jpg"
    g, s, gr = separate(SRC)
    print("gold polys", len(g), "silk polys", len(s))
    print("gold total pts", sum(len(p) for p in g))
    print("silk total pts", sum(len(p) for p in s))
