# -*- coding: utf-8 -*-
"""位图小工具：泛洪填充 / 填洞（Pillow 13 的 ImageDraw.floodfill 在该环境失效，改为自实现）"""
import numpy as np
from PIL import Image, ImageFilter
from collections import deque


def dilate(m, k):
    return np.asarray(Image.fromarray(m.astype(np.uint8) * 255, "L")
                      .filter(ImageFilter.MaxFilter(k))) > 127


def erode(m, k):
    return np.asarray(Image.fromarray(m.astype(np.uint8) * 255, "L")
                      .filter(ImageFilter.MinFilter(k))) > 127


def close(m, k):
    return erode(dilate(m, k), k)


def flood(passable, seeds):
    """4 连通泛洪，passable 为布尔图；返回可达区域"""
    h, w = passable.shape
    seen = np.zeros((h, w), bool)
    dq = deque()
    flat = passable.ravel()
    seenf = seen.ravel()
    for x, y in seeds:
        if 0 <= x < w and 0 <= y < h and passable[y, x]:
            i = y * w + x
            if not seenf[i]:
                seenf[i] = True
                dq.append(i)
    while dq:
        i = dq.popleft()
        y, x = divmod(i, w)
        if y > 0:
            j = i - w
            if flat[j] and not seenf[j]:
                seenf[j] = True; dq.append(j)
        if y < h - 1:
            j = i + w
            if flat[j] and not seenf[j]:
                seenf[j] = True; dq.append(j)
        if x > 0:
            j = i - 1
            if flat[j] and not seenf[j]:
                seenf[j] = True; dq.append(j)
        if x < w - 1:
            j = i + 1
            if flat[j] and not seenf[j]:
                seenf[j] = True; dq.append(j)
    return seen


def fill_holes(m):
    """填掉不与边界连通的空洞"""
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), bool)
    pad[1:-1, 1:-1] = m
    outside = flood(~pad, [(0, 0)])
    return ~outside[1:-1, 1:-1] & pad[1:-1, 1:-1] | m


def components(passable, min_area=1):
    """返回 [(面积, 布尔图)]，按面积降序"""
    h, w = passable.shape
    todo = passable.copy()
    out = []
    ys, xs = np.nonzero(todo)
    for y, x in zip(ys, xs):
        if not todo[y, x]:
            continue
        reg = flood(todo, [(x, y)])
        todo &= ~reg
        out.append((int(reg.sum()), reg))
    out.sort(key=lambda t: -t[0])
    return [(a, r) for a, r in out if a >= min_area]
