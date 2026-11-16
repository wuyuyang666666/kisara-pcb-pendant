# -*- coding: utf-8 -*-
"""v10 生产文件：正面沿用 v9 的设计，背面换成 back10 的新版式。

输出 build/gerber10/，不覆盖 gerber3(v8) / gerber9(v9)。
工艺仍是：白色阻焊整板 + 黑色丝印 + 沉金开窗；6 层 + 沉金不变。
  GTS = 正面沉金点睛 + 金环      GTO = 正面黑丝印
  GBS = 背面金环 + X 发饰 + 字组  GBO = 背面黑丝印细点线（v9 为空文件）
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design9 as D
import back10 as B
import bmp
from grb import Grb, emit_rings

ROOT = D.ROOT
OUT = os.path.join(ROOT, "build", "gerber10")
SCALE, SRC = D.SCALE, D.SRC


def board_bitmap(inset_mm=0.0):
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    pts = [(mx / SCALE + SRC / 2, SRC / 2 - my / SCALE)
           for mx, my in D.board_outline()]
    d.polygon(pts, fill=255)
    m = np.asarray(img) > 127
    if inset_mm > 0:
        k = int(round(inset_mm / SCALE)) * 2 + 1
        m = bmp.erode(m, k)
    return m


def holes_bitmap(m, r_mm):
    hx, hy, hd = D.hole()
    img = Image.fromarray(m.astype(np.uint8) * 255, "L")
    d = ImageDraw.Draw(img)
    r = r_mm / SCALE
    cx = hx / SCALE + SRC / 2
    cy = SRC / 2 - hy / SCALE
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    return np.asarray(img) > 127


def write_dxf(poly, path, layer="OUTLINE"):
    L = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
         "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES",
         "0", "LWPOLYLINE", "8", layer, "90", str(len(poly)), "70", "1"]
    for x, y in poly:
        L += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    m = D.build_masks()
    bg, bs = B.bottom_gold_mask(), B.bottom_silk_mask()
    print("front: gold=%.1fmm2 silk=%.1fmm2 | back: gold=%.1fmm2 silk=%.1fmm2" %
          (m["gold"].sum() * SCALE ** 2, m["silk"].sum() * SCALE ** 2,
           bg.sum() * SCALE ** 2, bs.sum() * SCALE ** 2))

    gold_rings = D.rings_of(m["gold"], eps=0.05, min_area_px=8)
    silk_rings = D.rings_of(m["silk"], eps=0.07, min_area_px=10)
    bgold_rings = D.rings_of(bg, eps=0.05, min_area_px=8)
    bsilk_rings = D.rings_of(bs, eps=0.035, min_area_px=6)
    print("rings: front gold=%d silk=%d | back gold=%d silk=%d" %
          (len(gold_rings), len(silk_rings), len(bgold_rings), len(bsilk_rings)))

    copper = holes_bitmap(board_bitmap(0.25), D.HOLE_D / 2 + 0.9)
    cu_rings = D.rings_of(copper, eps=0.3, min_area_px=50)
    outline = D.board_outline()

    # ---------- 6 层铜：全板铺铜
    for name, note in (("GTL", "L1 top copper"), ("G2", "L2 inner copper plane"),
                       ("G3", "L3 inner copper plane"), ("G4", "L4 inner copper plane"),
                       ("G5", "L5 inner copper plane"), ("GBL", "L6 bottom copper")):
        g = Grb(note)
        emit_rings(g, cu_rings)
        g.save(os.path.join(OUT, f"kisara_medallion.{name}"))

    # ---------- 顶层阻焊开窗 = 正面沉金
    g = Grb("top solder mask opening / ENIG")
    emit_rings(g, gold_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTS"))

    # ---------- 底层阻焊开窗 = 背面金环 + X 发饰 + 字组
    g = Grb("bottom solder mask opening / ENIG")
    emit_rings(g, bgold_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBS"))

    # ---------- 顶层丝印 = 正面黑丝印
    g = Grb("top silkscreen / black")
    emit_rings(g, silk_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTO"))

    # ---------- 底层丝印 = 背面细点线（v9 为空）
    g = Grb("bottom silkscreen / black dot ring")
    emit_rings(g, bsilk_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBO"))

    # ---------- 板框
    g = Grb("board outline")
    g.path(outline + [outline[0]], 0.10)
    g.save(os.path.join(OUT, "kisara_medallion.GKO"))

    # ---------- 钻孔
    hx, hy, hd = D.hole()
    with open(os.path.join(OUT, "kisara_medallion.TXT"), "w", encoding="ascii", newline="\n") as f:
        f.write("M48\n;EXCELLON\nFMAT,2\nMETRIC,TZ\n")
        f.write(f"T1C{hd:.3f}\n%\nG90\nG05\nT1\n")
        f.write(f"X{hx:.3f}Y{hy:.3f}\nT0\nM30\n")

    write_dxf(outline, os.path.join(ROOT, "build", "medallion_outline.dxf"))
    print("gerber saved to", OUT)
    return m


if __name__ == "__main__":
    main()
