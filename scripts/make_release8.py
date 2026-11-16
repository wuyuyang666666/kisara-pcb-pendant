# -*- coding: utf-8 -*-
"""v8 生产文件：6 层 Gerber + 钻孔 + 板框 DXF

工艺：白色阻焊整板 + 黑色丝印（线条/块面）+ 沉金开窗（金瞳/领结/菱形/金环）
正面 GTS = 沉金开窗；GTO = 黑丝印
背面 GBS = 金环 + 金色 KISARA 字；GBO 为空
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import design8 as D
import bmp
from grb import Grb, emit_rings

ROOT = D.ROOT
OUT = os.path.join(ROOT, "build", "gerber3")
SCALE = D.SCALE
SRC = D.SRC

FONTS = [
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\bahnschrift.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
]


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


def load_font(size_px):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size_px)
    return ImageFont.load_default()


def text_mask(text, size_px, cy_px):
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    font = load_font(size_px)
    bb = d.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    x = (SRC - w) / 2 - bb[0]
    y = cy_px - bb[3] + (bb[3] - bb[1]) / 2
    d.text((x, y), text, font=font, fill=255)
    return np.asarray(img) > 127


def bottom_gold_mask():
    """背面沉金开窗：金环 + KISARA + 副标题 + 两侧小菱形（呼应正面）"""
    ring = D.annulus(D.RING_IN, D.RING_OUT) & D.circle_mask()
    tm = text_mask("KISARA", size_px=104, cy_px=int(SRC * 0.48))
    sub = text_mask("ENGAGE KISS", size_px=40, cy_px=int(SRC * 0.60))
    dm = Image.new("L", (SRC, SRC), 0)
    dd = ImageDraw.Draw(dm)
    for cx in (int(SRC * 0.23), int(SRC * 0.77)):
        cy, s = int(SRC * 0.48), 14
        dd.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=255)
    return (ring | tm | sub | (np.asarray(dm) > 127)) & D.circle_mask()


def main():
    os.makedirs(OUT, exist_ok=True)
    m = D.build_masks()
    print("masks: gold=%dpx (%.1fmm2)  silk=%dpx (%.1fmm2)" %
          (m["gold"].sum(), m["gold"].sum() * SCALE ** 2,
           m["silk"].sum(), m["silk"].sum() * SCALE ** 2))

    gold_rings = D.rings_of(m["gold"], eps=0.05, min_area_px=8)
    silk_rings = D.rings_of(m["silk"], eps=0.07, min_area_px=10)
    print("rings: gold=%d silk=%d" % (len(gold_rings), len(silk_rings)))

    copper = holes_bitmap(board_bitmap(0.25), D.HOLE_D / 2 + 0.9)
    cu_rings = D.rings_of(copper, eps=0.3, min_area_px=50)
    board_rings = D.rings_of(board_bitmap(0.0), eps=0.12, min_area_px=50)
    outline = D.board_outline()

    # ---------- 6 层铜：全板铺铜（装饰板铜配平，层序无关）
    for name, note in (("GTL", "L1 top copper"), ("G2", "L2 inner copper plane"),
                       ("G3", "L3 inner copper plane"), ("G4", "L4 inner copper plane"),
                       ("G5", "L5 inner copper plane"), ("GBL", "L6 bottom copper")):
        g = Grb(note)
        emit_rings(g, cu_rings)
        g.save(os.path.join(OUT, f"kisara_medallion.{name}"))

    # ---------- 顶层阻焊开窗 = 沉金点睛 + 金环
    g = Grb("top solder mask opening / ENIG")
    emit_rings(g, gold_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTS"))

    # ---------- 底层阻焊开窗 = 金环 + 金色文字
    g = Grb("bottom solder mask opening / ENIG")
    emit_rings(g, D.rings_of(bottom_gold_mask(), eps=0.08, min_area_px=8))
    g.save(os.path.join(OUT, "kisara_medallion.GBS"))

    # ---------- 顶层丝印 = 黑丝印线条/块面
    g = Grb("top silkscreen / black")
    emit_rings(g, silk_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTO"))

    # ---------- 底层丝印：留空（背面全部用沉金表达）
    g = Grb("bottom silkscreen / none")
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


def write_dxf(poly, path, layer="OUTLINE"):
    L = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
         "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES",
         "0", "LWPOLYLINE", "8", layer, "90", str(len(poly)), "70", "1"]
    for x, y in poly:
        L += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
