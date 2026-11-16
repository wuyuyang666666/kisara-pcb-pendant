#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪影 → 可制造板框多边形
输入：黑色剪影 PNG（白底）
输出：mm 坐标的闭合多边形

工艺约束（1.6mm FR4 / CNC 铣边 / 沉金）：
  - 最小特征宽度 >= 1.5mm（铣刀 φ1.0，留余量）
  - 挂孔边缘到板边 >= 3.0mm
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image
import vectorize as V
import contour as C


def ring_to_mm(ring, px_per_mm, flip_y=True, height_px=None):
    """像素环 -> mm 环（y 轴翻转）"""
    out = []
    for x, y in ring:
        yy = (height_px - y) if flip_y else y
        out.append((x / px_per_mm, yy / px_per_mm))
    return out


def measure_width_px(ring_px, bw, max_probe=200):
    """在像素坐标系下测量每个轮廓点的局部厚度（像素）"""
    w, h = bw.size
    px = bw.load()
    n = len(ring_px)
    out = []
    for i in range(n):
        x, y = ring_px[i]
        x0, y0 = ring_px[(i - 4) % n]
        x1, y1 = ring_px[(i + 4) % n]
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty)
        if L < 1e-9:
            out.append(max_probe)
            continue
        nx, ny = -ty / L, tx / L
        best = 0
        for sgn in (1, -1):
            d = 0
            cx, cy = x, y
            while d < max_probe:
                cx += nx * sgn
                cy += ny * sgn
                d += 1
                ix, iy = int(cx), int(cy)
                if not (0 <= ix < w and 0 <= iy < h) or px[ix, iy] == 0:
                    break
            best = max(best, d)
        out.append(best)
    return out


def build(src, target_width_mm=60.0, open_px=12, close_px=0,
          smooth_iter=2, rdp_eps=1.6):
    im = Image.open(src)
    bw = V.binarize(im)
    if close_px:
        bw = V.morph(bw, close_px, "close")
    if open_px:
        bw = V.morph(bw, open_px, "open")

    bw = V.largest_component(bw)
    bw = V.fill_holes(bw)

    bb = bw.getbbox()
    bw = bw.crop(bb)

    rings = C.extract(bw)
    if not rings:
        raise RuntimeError("无轮廓")
    ring_px = C.pick_main_ring(rings)

    widths_px = measure_width_px(ring_px, bw)

    scale = bw.width / target_width_mm      # px per mm
    height_mm = bw.height / scale

    # 简化 + 平滑
    simp = V.rdp(ring_px, rdp_eps)
    simp = V.chaikin(simp, smooth_iter)

    poly = [(x / scale, height_mm - y / scale) for x, y in simp]

    ws = sorted(widths_px)
    st = {
        "size_mm": (target_width_mm, height_mm),
        "px": bw.size,
        "pts_raw": len(ring_px),
        "pts_final": len(poly),
        "min_w_mm": ws[len(ws) // 20] / scale,
        "p05_w_mm": ws[len(ws) // 20] / scale,
        "median_w_mm": ws[len(ws) // 2] / scale,
        "scale_px_per_mm": scale,
    }
    return bw, ring_px, poly, st


if __name__ == "__main__":
    SRC = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\Pure_black_solid_silhouette_of_2026-11-05T14-26-32.png"
    for op in (0, 8, 12, 16, 20):
        bw, ring, poly, st = build(SRC, 60.0, open_px=op)
        print(f"open{op:<3d} pts={st['pts_final']:4d} minW={st['min_w_mm']:.2f}mm "
              f"medianW={st['median_w_mm']:.2f}mm size={st['size_mm'][0]:.0f}x{st['size_mm'][1]:.0f}")
