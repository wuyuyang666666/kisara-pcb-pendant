#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主流程：生成木更 PCB 挂件的板框生产文件
输出：
  build/kisara_outline.dxf     板框（LWPOLYLINE 闭合，mm）
  build/kisara_outline.svg     矢量预览
  build/kisara_outline.json    几何数据（供后续层使用）
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import build_shape as B
import export as X

SRC = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\assets\Pure_black_solid_silhouette_of_2026-11-05T14-26-32.png"
OUTDIR = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13\build"

# 工艺参数
TARGET_W = 55.0        # 成品宽度 mm
OPEN_PX = 11           # 开运算半径（去细丝）
HOLE_D = 3.0           # 挂孔直径
HOLE_EDGE_MIN = 5.0    # 孔心距板边最小距离


def find_top_y(poly, cx, half_w=3.0):
    """在水平窗口内找轮廓最高点"""
    ys = [y for x, y in poly if abs(x - cx) <= half_w]
    return max(ys) if ys else max(y for _, y in poly)


def centroid_x(poly):
    """按轮廓面积重心求水平中心"""
    a = cx = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
    return cx / (3 * a) if abs(a) > 1e-9 else sum(p[0] for p in poly) / n


def add_top_ring(poly, cx, r_out, cut_depth=2.4):
    """
    把轮廓顶部（y > top-cut_depth 的部分）投影到以 (cx, top-cut_depth) 为心、
    半径 r_out 的圆弧上，形成头顶挂耳。
    只改变半径方向的位置，不增删顶点，不会自交。
    """
    top = max(y for _, y in poly)
    cy = top - cut_depth
    out = []
    for x, y in poly:
        if y > cy:
            dx, dy = x - cx, y - cy
            L = math.hypot(dx, dy)
            if L < 1e-6:
                out.append((cx, cy + r_out))
            else:
                out.append((cx + dx / L * r_out, cy + dy / L * r_out))
        else:
            out.append((x, y))
    return out, cy


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    bw, ring_px, poly, st = B.build(SRC, TARGET_W, open_px=OPEN_PX)
    print(f"轮廓: {st['pts_final']} 点  {st['size_mm'][0]:.1f} x {st['size_mm'][1]:.1f} mm  "
          f"minW={st['min_w_mm']:.2f}mm  medianW={st['median_w_mm']:.2f}mm")

    # 归一化到原点 (0,0)
    minx = min(p[0] for p in poly)
    miny = min(p[1] for p in poly)
    poly = [(x - minx, y - miny) for x, y in poly]

    w = max(p[0] for p in poly)
    h = max(p[1] for p in poly)

    cx = centroid_x(poly)

    # 顶部圆环挂耳
    RING_R = 3.9
    poly, ring_cy = add_top_ring(poly, cx, RING_R)
    w = max(p[0] for p in poly)
    h = max(p[1] for p in poly)
    top_y = max(p[1] for p in poly)
    hole = (round(cx, 2), round(ring_cy, 2), HOLE_D / 2)

    print(f"板框 {w:.1f} x {h:.1f} mm  重心x={cx:.2f}  顶边y={top_y:.2f}  挂孔={hole}")

    # 校验：孔是否完全在实体内（用射线法粗测四个方向）
    def inside(px, py):
        c = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1) + x1):
                c = not c
        return c

    ok = all(inside(hole[0] + dx, hole[1] + dy)
             for dx in (-hole[2], 0, hole[2]) for dy in (-hole[2], 0, hole[2]))
    print("挂孔落在实体内:", ok)

    # ---- DXF
    dxf_path = os.path.join(OUTDIR, "kisara_outline.dxf")
    X.to_dxf([{"pts": poly, "closed": True, "layer": "BOARD_OUTLINE"}], dxf_path)

    # ---- SVG（板框 + 孔）
    svg_path = os.path.join(OUTDIR, "kisara_outline.svg")
    hole_poly = circular(hole[0], hole[1], hole[2], 48)
    X.to_svg(
        [{"pts": poly, "closed": True, "fill": "#1a1a1a", "stroke": "#d4af69",
          "stroke_width": 0.2, "id": "board"},
         {"pts": hole_poly, "closed": True, "fill": "#f6f6f4", "stroke": "#d4af69",
          "stroke_width": 0.15, "id": "mount_hole"}],
        (w, h), svg_path, title="Kisara PCB pendant - board outline")

    # ---- JSON
    js = {
        "size_mm": [round(w, 3), round(h, 3)],
        "outline": [(round(x, 3), round(y, 3)) for x, y in poly],
        "mount_hole": {"cx": hole[0], "cy": hole[1], "d": HOLE_D, "type": "NPTH"},
        "process": {
            "target_width_mm": TARGET_W,
            "open_radius_px": OPEN_PX,
            "min_feature_mm": round(st["min_w_mm"], 2),
            "median_feature_mm": round(st["median_w_mm"], 2),
            "point_count": st["pts_final"],
        },
    }
    with open(os.path.join(OUTDIR, "kisara_outline.json"), "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)

    print("导出完成:", dxf_path, svg_path)


def circular(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


if __name__ == "__main__":
    main()
