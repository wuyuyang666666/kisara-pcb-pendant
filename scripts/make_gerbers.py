#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成嘉立创可直接下单的 6 层 Gerber 全套

层规划（6 层，哑黑阻焊 + 沉金 + 白丝印）
  L1 GTL  : 整板铺铜（板框形状）
  L2 G2   : 整板铺铜（地平面）
  L3 G3   : 整板铺铜 + 隐藏彩蛋（负极性挖空，透光可见）
  L4 G4   : 整板铺铜（电源平面）
  L5 G5   : 整板铺铜（地平面）
  L6 GBL  : 整板铺铜
  GTS     : L1 阻焊开窗 = 金色图案
  GBS     : L6 阻焊开窗 = 背面金色心形
  GTO     : L1 丝印 = 眼中高光
  GKO     : 板框
  TXT     : 钻孔（Φ3.0 NPTH 挂孔）
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import artwork as A
import gerber as G

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
OUT = os.path.join(ROOT, "build", "gerber")
JSON = os.path.join(ROOT, "build", "kisara_outline.json")

BOARD_W = 0.10
CW = 0.10


def ell(cx, cy, rx, ry, n=64):
    return [(cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def star(cx, cy, r_out, r_in, n=5):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi / 2 + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def main():
    os.makedirs(OUT, exist_ok=True)
    d = json.load(open(JSON, encoding="utf-8"))
    poly = d["outline"]
    hole = d["mount_hole"]
    W, H = d["size_mm"]

    items = A.build(cx=d.get("axis_x", 27.65))
    golds = [it["pts"] for it in items if it["kind"] == "gold" and len(it["pts"]) >= 3]
    silks = [it["pts"] for it in items if it["kind"] == "silk" and len(it["pts"]) >= 3]

    # ---------------- 板框 GKO ----------------
    g = G.Gerber("Board outline, 6 layer art board")
    g.aperture(10, "C", (BOARD_W,))
    g.polyline(poly, 10, closed=True)
    g.save(os.path.join(OUT, "kisara.GKO"))

    # ---------------- 各铜层 ----------------
    layers = [("kisara.GTL", "L1 Top copper"),
              ("kisara.G2", "L2 Inner1 GND"),
              ("kisara.G3", "L3 Inner2 ART"),
              ("kisara.G4", "L4 Inner3 PWR"),
              ("kisara.G5", "L5 Inner4 GND"),
              ("kisara.GBL", "L6 Bottom copper")]
    for fn, name in layers:
        g = G.Gerber(name)
        g.fill([poly])
        g.save(os.path.join(OUT, fn))

    # ---------------- L3 隐藏彩蛋（负极性挖空） ----------------
    g = G.Gerber("L3 hidden artwork (clear)")
    # 先铺满，再挖图案：图案处无铜 -> 强光下透光可见
    g.fill([poly])
    g.lines.append("%LPC*%")           # 切负极性
    cx = d.get("axis_x", 27.65)
    # 五角星 + 两个小圆 = "契约印记"
    g.fill([star(cx, 70.0, 5.2, 2.2, 5)])
    g.fill([ell(cx - 8.5, 62.0, 1.6, 1.6, 32)])
    g.fill([ell(cx + 8.5, 62.0, 1.6, 1.6, 32)])
    g.lines.append("%LPD*%")
    g.save(os.path.join(OUT, "kisara.G3"))

    # ---------------- L1 阻焊开窗 = 金色图案 ----------------
    g = G.Gerber("L1 solder mask (open = gold)")
    g.fill(golds)
    g.save(os.path.join(OUT, "kisara.GTS"))

    # ---------------- L6 阻焊开窗 = 背面心形 ----------------
    g = G.Gerber("L6 solder mask (open = gold heart)")
    heart = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        heart.append((cx + x * 0.46, 58.5 + y * 0.46))
    g.fill([heart])
    g.save(os.path.join(OUT, "kisara.GBS"))

    # ---------------- 丝印 ----------------
    g = G.Gerber("L1 silkscreen")
    if silks:
        g.fill(silks)
    g.save(os.path.join(OUT, "kisara.GTO"))

    # ---------------- 钻孔 ----------------
    G.excellon([(hole["cx"], hole["cy"], hole["d"])],
               os.path.join(OUT, "kisara.TXT"))

    print(f"生成 {len(os.listdir(OUT))} 个文件 -> {OUT}")
    for f in sorted(os.listdir(OUT)):
        sz = os.path.getsize(os.path.join(OUT, f))
        print(f"  {f:14s} {sz:>8d} B")


if __name__ == "__main__":
    main()
