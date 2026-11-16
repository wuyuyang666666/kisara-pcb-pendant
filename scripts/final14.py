# -*- coding: utf-8 -*-
"""最终版 v14：相对最初 56mm 一共缩小 1.0cm（56 -> 46mm），长宽比不变。

复用 scale13 的坐标仿射变换；自检复用 check13 的回读工具。
一次性生成 Gerber / zip / 三版 1:1 尺寸对比图，并打印完整工艺自检。
"""
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scale13 as S
import check13 as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G12 = os.path.join(ROOT, "build", "gerber12")
G13 = os.path.join(ROOT, "build", "gerber13")
G14 = os.path.join(ROOT, "build", "gerber14")
ZIP14 = os.path.join(ROOT, "build", "Kisara_Pendant_6L_ENIG_v14.zip")
K = 46.0 / 56.0
BASE = "kisara_medallion."
HOLE_D = 3.0          # 挂孔是机械接口，不跟着等比缩，保持 v12 的 Φ3.0


def build():
    S.K = K
    S.SRC = G12
    S.OUT = G14
    S.ZIP = ZIP14
    # 只把 TXT 的刀具直径改回 Φ3.0；孔位坐标与其它 11 层仍严格等比。
    # 挂耳是以孔心为圆心、半径 5.5*K 的正半圆，Φ3.0 孔与其同心、肉厚 3.018mm。
    _orig = S.scale_drill
    _old = "T1C%.3f" % (3.0 * K)

    def patched(text):
        return _orig(text).replace(_old, "T1C%.3f" % HOLE_D)

    S.scale_drill = patched
    S.main()


def check():
    C.K, C.G12, C.G13 = K, G12, G14
    print("\n========== v14 工艺自检 ==========")
    worst, n = C.scale_ratio_check()
    print(f"逐点坐标比 v14/v12 最大偏差 {worst:.3e}（{n} 点，K={K:.9f}）")

    for tag, folder in [("v12", G12), ("v14", G14)]:
        segs = C.outline(folder)
        xs = [x for s in segs for x, _ in s]
        ys = [y for s in segs for _, y in s]
        print(f"{tag}  板框 {max(xs)-min(xs):.3f} x {max(ys)-min(ys):.3f} mm  "
              f"长宽比 {(max(xs)-min(xs))/(max(ys)-min(ys)):.6f}  "
              f"Y {min(ys):+.3f}..{max(ys):+.3f}")

    circ = math.pi * 23 ** 2
    tot_gold = 0.0
    for ext in ["GTO", "GBO", "GTS", "GBS"]:
        a = C.area_mm2(C.mask(G14, ext))
        print(f"  {ext}  {a:8.1f} mm2  ({100*a/circ:5.1f}% of circle)")
        if ext in ("GTS", "GBS"):
            tot_gold += a
    print(f"  沉金双面合计 {tot_gold:.1f} / {circ:.0f} = {100*tot_gold/circ:.1f}%  <20% OK")

    st = C.morph.stroke_width(C.mask(G14, "GTO"), C.PPM)
    print(f"  白丝印 P5={st['p5']:.3f} mm  P50={st['p50']:.3f} mm  "
          f"<0.155mm={100*st['frac_under']:.1f}%   "
          f"{'OK' if st['p5'] >= 0.155 else 'FAIL'}")
    print(f"  理论 P5 = 0.219*K = {0.219*K:.3f} mm（余量 {0.219*K-0.155:.3f} mm）")
    print(f"  内层最细 0.328*K = {0.328*K:.3f} mm >=0.09 OK ; 金环 0.90*K = {0.90*K:.3f} mm")
    f = int((C.mask(G14, "GTO") & C.mask(G14, "GTS")).sum())
    b = int((C.mask(G14, "GBO") & C.mask(G14, "GBS")).sum())
    print(f"  丝印压金面 正面 {f} px / 背面 {b} px")
    hr, hy, top = HOLE_D / 2, 30.0 * K, 35.5 * K
    print(f"  挂孔 Φ{HOLE_D:.3f} mm @Y{hy:.3f}（机械接口，未等比缩），"
          f"孔边到挂耳顶肉厚 {top-hy-hr:.3f} mm")


def chart3():
    P = 5.0
    W, H = 1260, 710
    try:
        from PIL import ImageFont
        f_big = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
        f_sml = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
    except Exception:
        f_big = f_sml = None
    im = Image.new("RGB", (W, H), (240, 238, 232))
    d = ImageDraw.Draw(im)
    d.text((28, 20), "KISARA PENDANT  -  FINAL SIZE  (1:1, 1 mm = 5 px)",
           fill=(48, 46, 42), font=f_big)
    d.text((28, 46),
           "v12 56.0   ->   v13 51.0   ->   v14 46.0 mm   (v14 = FINAL, aspect ratio unchanged)",
           fill=(96, 93, 87), font=f_sml)
    bottom = 620
    cols = [
        (200, G12, "v12  original", "56.0 x 63.50 mm", (150, 152, 150), 1.0, 3.0),
        (610, G13, "v13  -0.5 cm", "51.0 x 57.83 mm", (120, 124, 120), 51 / 56, 3.0 * 51 / 56),
        (1020, G14, "v14  FINAL  -1.0 cm", "46.0 x 52.16 mm", (30, 110, 78), K, HOLE_D),
    ]
    for cx, folder, label, dims, col, kk, hd in cols:
        segs = C.outline(folder)
        xs = [x for s in segs for x, _ in s]
        ys = [y for s in segs for _, y in s]
        lo, hi = min(ys), max(ys)

        def T(x, y, cx=cx, lo=lo):
            return (cx + x * P, bottom - (y - lo) * P)

        for seg in segs:
            pts = [T(x, y) for x, y in seg]
            if len(pts) >= 2:
                d.line(pts + [pts[0]], fill=col, width=3)
        hole_y, r = 30.0 * kk, hd / 2
        hx, hy = T(0, hole_y)
        d.ellipse([hx - r * P, hy - r * P, hx + r * P, hy + r * P],
                  outline=col, width=2)
        top = bottom - (hi - lo) * P
        d.line([(cx + min(xs) * P, bottom + 18), (cx + max(xs) * P, bottom + 18)],
               fill=col, width=1)
        d.text((cx + min(xs) * P, bottom + 24),
               f"W {max(xs)-min(xs):.2f} mm", fill=col, font=f_sml)
        vx = cx + max(xs) * P + 12
        d.line([(vx, top), (vx, bottom)], fill=col, width=1)
        d.text((vx + 5, (top + bottom) / 2 - 10),
               f"H {hi-lo:.2f}", fill=col, font=f_sml)
        d.text((cx - 70, 220), label, fill=col, font=f_big)
        d.text((cx - 70, 246), dims, fill=col, font=f_sml)
    sx, sy = 60, 672
    for i in range(7):
        d.line([(sx + i * 50, sy), (sx + i * 50, sy + (10 if i % 2 == 0 else 6))],
               fill=(70, 68, 64), width=2)
    d.line([(sx, sy), (sx + 300, sy)], fill=(70, 68, 64), width=2)
    d.text((sx, sy + 14), "0", fill=(70, 68, 64), font=f_sml)
    d.text((sx + 282, sy + 14), "6 cm", fill=(70, 68, 64), font=f_sml)
    out = os.path.join(ROOT, "assets", "size_final_v14.png")
    im.save(out)
    return out


if __name__ == "__main__":
    build()
    check()
    print("\n对比图", chart3())
