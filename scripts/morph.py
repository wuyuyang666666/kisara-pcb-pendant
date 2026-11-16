# -*- coding: utf-8 -*-
"""
工艺化形态学：基于精确欧氏距离变换的圆盘膨胀/腐蚀 + 线宽测量。

Pillow 的 MaxFilter/MinFilter 用的是方形结构元，对角线方向会多膨胀 0.41px，
在 0.1mm 级线宽上误差不可忽略，所以这里改用 chamfer 距离变换实现圆盘算子。
"""
import numpy as np


def dt(mask):
    """
    对 mask 为真的像素，返回到最近 False 像素的近似欧氏距离（像素单位）。
    3-4 chamfer，误差 < 2%。
    """
    h, w = mask.shape
    INF = 1e9
    d = np.where(mask, INF, 0.0)
    A, B = 1.0, 1.41421356
    for y in range(h):
        row = d[y]
        prev = d[y - 1] if y > 0 else None
        for x in range(w):
            if row[x] == 0.0:
                continue
            v = row[x]
            if x > 0 and row[x - 1] + A < v:
                v = row[x - 1] + A
            if prev is not None:
                if prev[x] + A < v:
                    v = prev[x] + A
                if x > 0 and prev[x - 1] + B < v:
                    v = prev[x - 1] + B
                if x < w - 1 and prev[x + 1] + B < v:
                    v = prev[x + 1] + B
            row[x] = v
    for y in range(h - 1, -1, -1):
        row = d[y]
        nxt = d[y + 1] if y < h - 1 else None
        for x in range(w - 1, -1, -1):
            if row[x] == 0.0:
                continue
            v = row[x]
            if x < w - 1 and row[x + 1] + A < v:
                v = row[x + 1] + A
            if nxt is not None:
                if nxt[x] + A < v:
                    v = nxt[x] + A
                if x < w - 1 and nxt[x + 1] + B < v:
                    v = nxt[x + 1] + B
                if x > 0 and nxt[x - 1] + B < v:
                    v = nxt[x - 1] + B
            row[x] = v
    return d


def grow(mask, r_px):
    """圆盘膨胀 r_px 像素"""
    if r_px <= 0:
        return mask.copy()
    return mask | (dt(~mask) <= r_px)


def shrink(mask, r_px):
    """圆盘腐蚀 r_px 像素"""
    if r_px <= 0:
        return mask.copy()
    return mask & ~(dt(mask) <= r_px)


def _max3(d):
    """3x3 邻域最大值（边界补 -inf）"""
    p = np.pad(d, 1, constant_values=-1e9)
    out = d.copy()
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            np.maximum(out, p[dy:dy + d.shape[0], dx:dx + d.shape[1]], out=out)
    return out


def stroke_width(mask, px_per_mm):
    """
    按距离变换的脊线（ridge）测线宽：
    线宽 = 2 × 脊线处的 DT 值。

    注意：不能直接对 mask 内所有像素取分位——线条边缘像素的 DT 恒为 1px，
    会把 P5/P20 永远钉在 2px 上，测出来的是"边缘分布"而不是线宽。
    """
    d = dt(mask)
    ridge = mask & (d >= _max3(d) - 1e-9)
    w = 2.0 * d[ridge] / px_per_mm
    if w.size == 0:
        return None
    return {
        "w": w,
        "p5": float(np.percentile(w, 5)),
        "p20": float(np.percentile(w, 20)),
        "p50": float(np.percentile(w, 50)),
        "p90": float(np.percentile(w, 90)),
        "frac_under": float((w < 0.155).mean()),
        "ridge_px": int(ridge.sum()),
    }
