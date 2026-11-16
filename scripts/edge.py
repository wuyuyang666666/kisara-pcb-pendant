# -*- coding: utf-8 -*-
"""
像素边界追踪：把二值图的所有边界方向边连成闭合环。
比轮廓跟随算法稳，分叉处不会断，天然支持外环 + 孔洞。
"""
import numpy as np


def _edges(mask):
    m = mask
    up = np.zeros_like(m); up[1:] = m[:-1]
    dn = np.zeros_like(m); dn[:-1] = m[1:]
    lf = np.zeros_like(m); lf[:, 1:] = m[:, :-1]
    rt = np.zeros_like(m); rt[:, :-1] = m[:, 1:]

    segs = []   # (x0,y0,x1,y1)

    # 上边：向右
    ys, xs = np.nonzero(m & ~up)
    segs.append((xs, ys, xs + 1, ys))
    # 右边：向下
    ys, xs = np.nonzero(m & ~rt)
    segs.append((xs + 1, ys, xs + 1, ys + 1))
    # 下边：向左
    ys, xs = np.nonzero(m & ~dn)
    segs.append((xs + 1, ys + 1, xs, ys + 1))
    # 左边：向上
    ys, xs = np.nonzero(m & ~lf)
    segs.append((xs, ys + 1, xs, ys))

    x0 = np.concatenate([s[0] for s in segs])
    y0 = np.concatenate([s[1] for s in segs])
    x1 = np.concatenate([s[2] for s in segs])
    y1 = np.concatenate([s[3] for s in segs])
    return x0, y0, x1, y1


def rings(mask, min_points=4):
    """返回闭合环列表，点为像素角点坐标 (x, y)"""
    x0, y0, x1, y1 = _edges(mask)
    if len(x0) == 0:
        return []

    start = list(zip(x0.tolist(), y0.tolist()))
    end = list(zip(x1.tolist(), y1.tolist()))

    nxt = {}
    for i, s in enumerate(start):
        nxt.setdefault(s, []).append(i)

    used = bytearray(len(start))
    out = []
    for i in range(len(start)):
        if used[i]:
            continue
        ring = []
        cur = i
        guard = 0
        while True:
            used[cur] = 1
            ring.append(start[cur])
            e = end[cur]
            cands = nxt.get(e)
            if not cands:
                break
            nk = None
            for j in cands:
                if not used[j]:
                    nk = j
                    break
            if nk is None:
                break
            cur = nk
            guard += 1
            if guard > 5_000_000:
                break
        if len(ring) >= min_points:
            out.append(ring)
    return out


def area(r):
    s = 0.0
    n = len(r)
    for i in range(n):
        x1, y1 = r[i]
        x2, y2 = r[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0
