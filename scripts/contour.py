#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marching Squares 栅格轮廓提取
- 输入二值图（PIL "L"，255=前景）
- 输出若干闭合环（list of (x, y) 浮点像素坐标），外环逆时针、内环顺时针
- 二值图用边中点插值，输出为条带折线，后续用 RDP + Chaikin 平滑

相比 Moore / Wall-following 追踪，这种方法不会在细颈处卡死，
并且天然支持多环（外轮廓 + 内部孔洞）。
"""

from collections import defaultdict

# case 表: 角点编号 TL=8, TR=4, BR=2, BL=1
# 每条线段用边名表示: T=上, R=右, B=下, L=左
CASES = {
    0:  [],
    1:  [("L", "B")],
    2:  [("B", "R")],
    3:  [("L", "R")],
    4:  [("R", "T")],
    5:  [("L", "T"), ("B", "R")],   # 鞍点
    6:  [("B", "T")],
    7:  [("L", "T")],
    8:  [("T", "L")],
    9:  [("T", "B")],
    10: [("T", "R"), ("L", "B")],   # 鞍点
    11: [("T", "R")],
    12: [("L", "R")],
    13: [("R", "B")],
    14: [("L", "B")],
    15: [],
}


def _edge_point(name, x, y):
    if name == "T":
        return (x + 0.5, y)
    if name == "R":
        return (x + 1.0, y + 0.5)
    if name == "B":
        return (x + 0.5, y + 1.0)
    return (x, y + 0.5)          # L


def extract(bw):
    """返回 [ring, ...]，ring 为闭合点列（首尾相同）"""
    w, h = bw.size
    px = bw.load()

    def at(x, y):
        if x < 0 or y < 0 or x >= w or y >= h:
            return 0
        return 255 if px[x, y] else 0

    segs = []           # 每项 ((x1,y1),(x2,y2))
    for y in range(-1, h):
        for x in range(-1, w):
            tl = 8 if at(x, y) else 0
            tr = 4 if at(x + 1, y) else 0
            br = 2 if at(x + 1, y + 1) else 0
            bl = 1 if at(x, y + 1) else 0
            case = tl | tr | br | bl
            for e1, e2 in CASES.get(case, []):
                segs.append((_edge_point(e1, x, y), _edge_point(e2, x, y)))

    if not segs:
        return []

    # 端点量化后建图
    Q = 1000
    def key(p):
        return (round(p[0] * Q), round(p[1] * Q))

    adj = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        adj[key(a)].append((key(b), i))
        adj[key(b)].append((key(a), i))

    used = [False] * len(segs)
    rings = []

    for i0 in range(len(segs)):
        if used[i0]:
            continue
        a, b = segs[i0]
        used[i0] = True
        ring = [a, b]
        start_key = key(a)
        cur = key(b)
        prev = start_key
        guard = 0
        while guard < len(segs) * 4:
            guard += 1
            if cur == start_key:
                break
            nxt = None
            for nk, si in adj[cur]:
                if used[si]:
                    continue
                # 优先不走回头路
                if nk == prev and len(adj[cur]) > 1:
                    continue
                nxt = (nk, si)
                break
            if nxt is None:
                for nk, si in adj[cur]:
                    if not used[si]:
                        nxt = (nk, si)
                        break
            if nxt is None:
                break
            nk, si = nxt
            used[si] = True
            prev, cur = cur, nk
            ring.append((nk[0] / Q, nk[1] / Q))
        if len(ring) >= 4:
            rings.append(ring)

    return rings


def ring_area(ring):
    s = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def pick_main_ring(rings):
    """面积最大的环视为外轮廓"""
    if not rings:
        return None
    return max(rings, key=lambda r: abs(ring_area(r)))
