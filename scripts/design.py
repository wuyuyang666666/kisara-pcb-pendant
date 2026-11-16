#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木更 PCB 挂件 —— 几何定义模块
所有几何均为 mm 单位、原点在左下角、y 轴向上。
只生成多边形点列，供 SVG / DXF / Gerber 三种后端共用。

设计约束（1.6mm FR4，CNC 铣边 + 沉金）：
  - 任意实体处最小宽度 >= 2.0mm
  - 内角半径 >= 0.5mm
  - 挂孔边缘到板边 >= 3.0mm
"""

import math

# ---------------------------------------------------------------- 样条


def catmull_rom(pts, closed=True, samples_per_seg=12, tension=1.0):
    """Catmull-Rom 样条插值，返回平滑点列"""
    n = len(pts)
    if n < 3:
        return list(pts)
    out = []
    idx = range(n) if closed else range(n - 1)
    for i in idx:
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n] if closed else pts[min(i + 1, n - 1)]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t * tension
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t * tension
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def mirror_x(pts, axis=0.0):
    return [(2 * axis - x, y) for x, y in pts]


def poly_ellipse(cx, cy, rx, ry, n=36, rot=0.0):
    a = math.radians(rot)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(a) - y * math.sin(a),
                    cy + x * math.sin(a) + y * math.cos(a)))
    return out


def poly_ring(cx, cy, r_out, r_in, n=40):
    """圆环外轮廓（用于挖孔，Gerber 用 LPC 或直接给内轮廓）"""
    return poly_ellipse(cx, cy, r_out, r_out, n)


def offset_rect(x0, y0, x1, y1, r=0.0, n=8):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- 板框

# 右半边控制点：底中 → 胸 → 腰 → 肩 → 发束外缘 → 鬓角 → 脸颊 → 头顶 → 右角 → 挂耳 → 顶中
# 设计意图：钟形长发胸像；角短粗向上弯；顶中一个圆环状挂耳
CX = 22.0          # 中轴
HALF_OUTLINE = [
    (22.0, 4.0),      # 底中
    (27.0, 4.5),      # 底边右
    (32.0, 6.8),      # 胸下缘
    (34.5, 12.5),     # 腰（收）
    (37.2, 18.5),     # 胸外（放）
    (39.0, 25.0),     # 肩外
    (40.2, 31.0),     # 发束① 外扩
    (37.6, 36.5),     # 发束之间内收
    (40.6, 41.5),     # 发束② 外扩
    (38.0, 46.0),     # 内收
    (38.8, 50.5),     # 鬓角外
    (35.0, 54.5),     # 额头右
    (31.4, 57.2),     # 头顶右 / 角根
    (34.6, 58.9),     # 右角 根外
    (36.9, 67.6),     # 右角 尖
    (30.6, 60.0),     # 右角 根内
    (26.0, 60.6),     # 头顶
    (25.9, 64.0),     # 挂耳 右
    (22.0, 67.3),     # 挂耳 顶（中轴）
]


def board_outline(samples=16):
    """返回闭合板框多边形（外轮廓）"""
    right = catmull_rom(HALF_OUTLINE, closed=False, samples_per_seg=samples)
    left = mirror_x(list(reversed(right)), axis=CX)
    pts = right + left[1:]
    return pts


# ---------------------------------------------------------------- 挂孔

MOUNT_HOLE = (CX, 63.4, 1.5)   # cx, cy, r  -> Φ3.0 NPTH，位于头顶挂耳中心


# ---------------------------------------------------------------- 面部


def face_ellipse():
    """脸部（沉金填色）"""
    return poly_ellipse(CX, 47.5, 6.6, 8.2, 44)


def eyes():
    """双眼（阻焊开窗露金，杏仁形）"""
    left = [(CX - 4.4, 49.2), (CX - 3.2, 50.4), (CX - 1.5, 50.0),
            (CX - 2.2, 48.7), (CX - 3.6, 48.4)]
    left = catmull_rom(left, closed=True, samples_per_seg=10)
    return left, mirror_x(left, axis=CX)



if __name__ == "__main__":
    o = board_outline()
    print("outline pts:", len(o), "bbox:", [round(v, 2) for v in bbox(o)])
