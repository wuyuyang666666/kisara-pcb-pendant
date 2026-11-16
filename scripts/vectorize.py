#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木更 PCB 挂件 —— 剪影矢量化 / 可制造性处理
纯 PIL 实现（不依赖 numpy / opencv）

流程：
  1. 二值化
  2. 形态学闭运算（合并缝隙，保证结构强度）
  3. 形态学开运算（去除细发丝、手指等不可制造特征）
  4. 最大连通域保留 + 内部孔洞填充
  5. Moore 邻域轮廓追踪
  6. Douglas-Peucker 简化
  7. Chaikin 平滑
  8. 缩放至目标尺寸，输出闭合多边形
"""

import math
from collections import deque
from PIL import Image, ImageFilter, ImageDraw

# ---------------------------------------------------------------- 基础工具


def binarize(img, threshold=128):
    """前景（人物）-> 255，背景 -> 0"""
    g = img.convert("L")
    return g.point(lambda v: 255 if v < threshold else 0)


def largest_component(bw):
    """保留最大连通域（8 连通）"""
    w, h = bw.size
    px = bw.load()
    seen = bytearray(w * h)
    best, best_n = [], 0
    for y0 in range(h):
        for x0 in range(w):
            if px[x0, y0] == 0 or seen[y0 * w + x0]:
                continue
            comp, q = [], deque([(x0, y0)])
            seen[y0 * w + x0] = 1
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and px[nx, ny]:
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            if len(comp) > best_n:
                best, best_n = comp, len(comp)
    out = Image.new("L", (w, h), 0)
    p = out.load()
    for x, y in best:
        p[x, y] = 255
    return out


def fill_holes(bw):
    """填充内部孔洞：从边框泛洪背景，未被淹到的背景即为内部孔"""
    w, h = bw.size
    px = bw.load()
    reach = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if px[x, y] == 0 and not reach[y * w + x]:
                reach[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if px[x, y] == 0 and not reach[y * w + x]:
                reach[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not reach[ny * w + nx] and px[nx, ny] == 0:
                reach[ny * w + nx] = 1
                q.append((nx, ny))
    out = bw.copy()
    p = out.load()
    for y in range(h):
        for x in range(w):
            if px[x, y] == 0 and not reach[y * w + x]:
                p[x, y] = 255
    return out


def morph(bw, radius, mode, pad=None):
    """
    radius 单位 px，mode: close / open
    先加黑边 padding，避免 PIL 滤波器在图像边界外插产生白边伪影。
    """
    if radius <= 0:
        return bw
    k = radius * 2 + 1
    pad = pad or (radius * 3 + 2)
    w, h = bw.size
    canvas = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    canvas.paste(bw, (pad, pad))
    if mode == "close":                      # 膨胀 -> 腐蚀
        canvas = canvas.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    else:                                    # open: 腐蚀 -> 膨胀
        canvas = canvas.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    return canvas.crop((pad, pad, pad + w, pad + h))


# ---------------------------------------------------------------- 轮廓追踪

# Moore 邻域顺时针顺序
MOORE = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def trace_contour(bw):
    """Moore 邻域边界追踪，返回单条闭合轮廓点列（逆时针/顺时针不保证）"""
    w, h = bw.size
    px = bw.load()
    start = None
    for y in range(h):
        for x in range(w):
            if px[x, y]:
                start = (x, y)
                break
        if start:
            break
    if not start:
        return []

    contour = [start]
    prev_dir = 6  # 从左方进入（背景在左边）
    cur = start
    for _ in range(w * h * 4):
        found = False
        for i in range(8):
            d = (prev_dir + 5 + i) % 8   # 从回退方向开始顺时针扫
            nx, ny = cur[0] + MOORE[d][0], cur[1] + MOORE[d][1]
            if 0 <= nx < w and 0 <= ny < h and px[nx, ny]:
                prev_dir = d
                cur = (nx, ny)
                contour.append(cur)
                found = True
                break
        if not found:
            break
        if cur == start and len(contour) > 4:
            break
    return contour


# ---------------------------------------------------------------- 简化 / 平滑


def rdp(points, eps):
    """Douglas-Peucker（迭代版，避免递归深度问题）"""
    if len(points) < 3:
        return points[:]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue
        ax, ay = points[s]
        bx, by = points[e]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        best_i, best_d = -1, -1.0
        for i in range(s + 1, e):
            px, py = points[i]
            if norm < 1e-9:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > best_d:
                best_i, best_d = i, d
        if best_d > eps:
            keep[best_i] = True
            stack.append((s, best_i))
            stack.append((best_i, e))
    return [p for p, k in zip(points, keep) if k]


def chaikin(points, iterations=2, closed=True):
    """Chaikin 角切平滑"""
    pts = points[:]
    if closed and pts[0] == pts[-1]:
        pts = pts[:-1]
    for _ in range(iterations):
        out = []
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            p, q = pts[i], pts[(i + 1) % n]
            out.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            out.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        pts = out
    if closed:
        pts.append(pts[0])
    return pts


# ---------------------------------------------------------------- 形态统计


def min_feature_width(bw, sample_step=5):
    """
    估算最小特征宽度：沿外轮廓采样，沿内法向穿透到对边，
    取 5% 分位数作为「最薄处」的近似，用于工艺校验。
    """
    w, h = bw.size
    px = bw.load()
    contour = trace_contour(bw)
    n = len(contour)
    if n < 20:
        return 0.0

    def probe(x, y, dx, dy, limit=400):
        d = 0
        cx, cy = float(x), float(y)
        while d < limit:
            cx += dx
            cy += dy
            d += 1
            ix, iy = int(round(cx)), int(round(cy))
            if not (0 <= ix < w and 0 <= iy < h) or px[ix, iy] == 0:
                break
        return d

    thickness = []
    for i in range(0, n, sample_step):
        x, y = contour[i]
        x2, y2 = contour[(i + 3) % n]
        tx, ty = x2 - x, y2 - y
        L = math.hypot(tx, ty)
        if L < 1e-6:
            continue
        nx, ny = -ty / L, tx / L
        d1 = probe(x, y, nx, ny)
        d2 = probe(x, y, -nx, -ny)
        thickness.append(max(d1, d2))
    thickness.sort()
    return float(thickness[len(thickness) // 20]) if thickness else 0.0


# ---------------------------------------------------------------- 主流程


def build(src, out_prefix, target_width_mm=60.0,
          close_r=0, open_r=0, fill=True,
          rdp_eps=1.2, smooth=2, crop_bottom=None, debug_dir=None):
    im = Image.open(src)
    bw = binarize(im)

    if crop_bottom:
        bw = bw.crop((0, 0, bw.width, crop_bottom))

    if close_r:
        bw = morph(bw, close_r, "close")
    if open_r:
        bw = morph(bw, open_r, "open")

    bw = largest_component(bw)
    if fill:
        bw = fill_holes(bw)

    bbox = bw.getbbox()
    bw = bw.crop(bbox)

    contour = trace_contour(bw)
    if not contour:
        raise RuntimeError("未找到轮廓")

    # 像素 -> 多边形（y 轴翻转，图像向下为正 -> 工程向上为正）
    pts_px = [(float(x), float(y)) for x, y in contour]
    pts_px = rdp(pts_px, rdp_eps)
    pts_px = chaikin(pts_px, smooth)

    # 缩放：bbox 宽度 -> target_width_mm
    scale = target_width_mm / bw.width
    height_mm = bw.height * scale
    poly = [(x * scale, (bw.height - y) * scale) for x, y in pts_px]  # y 向上

    min_w_px = min_feature_width(bw)
    stats = {
        "px_size": (bw.width, bw.height),
        "size_mm": (target_width_mm, height_mm),
        "scale_mm_per_px": scale,
        "points_raw": len(contour),
        "points_final": len(poly),
        "min_feature_px": min_w_px,
        "min_feature_mm": min_w_px * scale,
    }
    return bw, poly, stats


if __name__ == "__main__":
    import sys
    src = sys.argv[1]
    bw, poly, st = build(src, "out", target_width_mm=60.0, close_r=18, open_r=6)
    for k, v in st.items():
        print(f"{k}: {v}")
