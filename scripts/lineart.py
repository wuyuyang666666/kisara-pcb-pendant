# -*- coding: utf-8 -*-
"""
从插画提取线稿：自适应阈值找“比周围暗”的像素 -> 细化成单像素骨架
-> 图遍历成折线 -> 简化。输出像素坐标折线，供后续转 mm / Gerber。
"""
import math
import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------- 基础工具

def box_mean(a, r):
    """积分图快速均值滤波"""
    h, w = a.shape
    pad = np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge")
    ii = pad.cumsum(0).cumsum(1)
    k = 2 * r + 1
    y0 = np.arange(h)[:, None]
    x0 = np.arange(w)[None, :]
    s = (ii[y0 + k, x0 + k] - ii[y0, x0 + k]
         - ii[y0 + k, x0] + ii[y0, x0])
    return s / (k * k)


def to_l(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    return 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]


def line_mask(img, t=34.0, k=9):
    """
    黑帽变换：灰度闭运算(先膨胀后腐蚀) - 原图。
    只保留“比周围更暗的细结构”——正是线稿的定义，
    对整体明暗渐变不敏感，比局部均值阈值稳定得多。
    """
    L = to_l(img)
    li = Image.fromarray(np.clip(L, 0, 255).astype(np.uint8), "L")
    closed = li.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    bh = np.asarray(closed, np.float32) - np.asarray(li, np.float32)
    return bh > t, bh


def drop_small(mask, min_area=14):
    """去掉小连通块（噪点、零碎高光）"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    ys, xs = np.nonzero(mask)
    maskb = mask.astype(bool)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        cnt = 0
        while stack:
            y, x = stack.pop()
            cnt += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and maskb[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = cur
                        stack.append((ny, nx))
        if cnt < min_area:
            leave = lab == cur
            maskb[leave] = False
    return maskb


# ---------------------------------------------------------------- 细化

def thin(mask, max_iter=60):
    """Zhang-Suen 细化"""
    img = np.pad(mask.astype(np.uint8), 1)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            p = img
            P2 = p[:-2, 1:-1]
            P3 = p[:-2, 2:]
            P4 = p[1:-1, 2:]
            P5 = p[2:, 2:]
            P6 = p[2:, 1:-1]
            P7 = p[2:, :-2]
            P8 = p[1:-1, :-2]
            P9 = p[:-2, :-2]
            B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
            seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            A = np.zeros(B.shape, np.int16)
            for i in range(8):
                A += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int16)
            c = img[1:-1, 1:-1]
            cond = (c > 0) & (B >= 2) & (B <= 6) & (A == 1)
            if step == 0:
                cond = cond & (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
            else:
                cond = cond & (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
            cond = cond.astype(bool)
            if cond.any():
                changed = True
                img[1:-1, 1:-1][cond] = 0
        if not changed:
            break
    return img[1:-1, 1:-1].astype(bool)


# ---------------------------------------------------------------- 骨架 -> 折线

NB = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def trace(skel, min_len=7):
    """把骨架拆成折线（像素坐标）"""
    H, W = skel.shape
    pts = {(int(y), int(x)) for y, x in zip(*np.nonzero(skel))}

    def nb(p):
        y, x = p
        return [(y + dy, x + dx) for dy, dx in NB if (y + dy, x + dx) in pts]

    deg = {p: len(nb(p)) for p in pts}
    used = set()
    paths = []

    def walk(start, first):
        path = [start, first]
        used.add((start, first))
        used.add((first, start))
        cur, prev = first, start
        while True:
            if deg.get(cur, 0) != 2:
                break
            nxt = [q for q in nb(cur) if q != prev]
            if not nxt:
                break
            q = nxt[0]
            if (cur, q) in used:
                break
            used.add((cur, q))
            used.add((q, cur))
            path.append(q)
            prev, cur = cur, q
        return path

    # 先从端点/交点出发
    for p in sorted(pts, key=lambda t: deg[t] != 1):
        if deg[p] == 2:
            continue
        for q in nb(p):
            if (p, q) in used:
                continue
            paths.append(walk(p, q))

    # 剩下的回路
    for p in pts:
        if deg[p] != 2:
            continue
        for q in nb(p):
            if (p, q) in used:
                continue
            paths.append(walk(p, q))

    out = [pth for pth in paths if len(pth) >= min_len]
    return out


def rdp(points, eps=0.9):
    """Douglas-Peucker 简化"""
    if len(points) < 3:
        return points
    p0, p1 = np.array(points[0], float), np.array(points[-1], float)
    d = p1 - p0
    n = np.hypot(*d)
    arr = np.array(points, float)
    if n < 1e-9:
        dist = np.hypot(*(arr - p0).T)
    else:
        v = arr - p0
        dist = np.abs(d[0] * v[:, 1] - d[1] * v[:, 0]) / n
    i = int(np.argmax(dist))
    if dist[i] > eps:
        left = rdp(points[:i + 1], eps)
        right = rdp(points[i:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]


def smooth(pl, k=1):
    """轻量平滑，抹掉骨架的锯齿台阶"""
    if len(pl) < 3:
        return pl
    arr = np.array(pl, float)
    for _ in range(k):
        arr[1:-1] = (arr[:-2] + 2 * arr[1:-1] + arr[2:]) / 4.0
    return [tuple(p) for p in arr]


def build(img, t=34.0, k=9, min_area=14, min_len=7, eps=0.9):
    mask, bh = line_mask(img, t=t, k=k)
    mask = drop_small(mask, min_area)
    skel = thin(mask)
    paths = trace(skel, min_len=min_len)
    paths = [rdp(smooth(p, 1), eps) for p in paths]
    paths = [p for p in paths if len(p) >= 2]
    # trace 内部用 (row, col)，对外统一成 (x, y)
    paths = [[(float(x), float(y)) for (y, x) in p] for p in paths]
    return paths, skel, mask
