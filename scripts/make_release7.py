# -*- coding: utf-8 -*-
"""v7 生产文件：6 层 Gerber + 钻孔 + 板框 DXF + 打包
工艺：黑阻焊 + 金色沉金（角色金像 + 金环 + 背面金心）+ 白丝印（眼睛高光 + 背面 KISARA 字）"""
import os, sys, math, json, zipfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import design7 as D
import bmp
from grb import Grb, emit_rings

ROOT = D.ROOT
OUT = os.path.join(ROOT, "build", "gerber3")
D_BOARD = D.D_BOARD
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
    pts = []
    for mx, my in D.board_outline():
        px = mx / SCALE + SRC / 2
        py = SRC / 2 - my / SCALE
        pts.append((px, py))
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


def heart_poly(cx=0.0, cy=0.0, s=8.0, n=64):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 16.0, cy + y * s / 16.0))
    return pts


def load_font(size_px):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size_px)
    return ImageFont.load_default()


def text_mask(text, size_px, cy_px):
    """白丝印文字位图（居中于 SRC 宽，纵向 cy_px 处为基线）"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    font = load_font(size_px)
    bb = d.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    x = (SRC - w) / 2 - bb[0]
    y = cy_px - bb[3] + (bb[3] - bb[1]) / 2
    d.text((x, y), text, font=font, fill=255)
    return np.asarray(img) > 127


def main():
    os.makedirs(OUT, exist_ok=True)
    m = D.build_masks()
    print("masks ok  gold=%.0fpx silk=%.0fpx" % (m["gold"].sum(), m["silk"].sum()))

    gold_rings = D.rings_of(m["gold"], min_area_px=8)
    silk_rings = D.rings_of(m["silk"], min_area_px=6)
    print("rings gold=%d silk=%d" % (len(gold_rings), len(silk_rings)))

    board = board_bitmap(0.0)
    copper = holes_bitmap(board_bitmap(0.25), D.HOLE_D / 2 + 0.9)
    cu_rings = D.rings_of(copper, eps=0.3, min_area_px=50)
    board_rings = D.rings_of(board, eps=0.12, min_area_px=50)
    outline = D.board_outline()

    # ---------- L1 顶层铜：整板铺铜
    g = Grb("L1 top copper")
    emit_rings(g, cu_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTL"))

    # ---------- L2~L5 内层：全部实心铜平面（6 层叠构铜配平，层序无关）
    for name in ("G2", "G3", "G4", "G5"):
        g = Grb(f"L{name[1]} inner copper plane")
        emit_rings(g, cu_rings)
        g.save(os.path.join(OUT, f"kisara_medallion.{name}"))

    # ---------- L6 底层铜
    g = Grb("L6 bottom copper")
    emit_rings(g, cu_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBL"))

    # ---------- 顶层阻焊：开窗 = 金像 + 金环
    g = Grb("top solder mask")
    emit_rings(g, gold_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTS"))

    # ---------- 底层阻焊：金心 + 金环
    hb = Image.new("L", (SRC, SRC), 0)
    hp = heart_poly(0, 0.5, 8.2)
    ImageDraw.Draw(hb).polygon(
        [(x / SCALE + SRC / 2, SRC / 2 - y / SCALE) for x, y in hp], fill=255)
    mask_bs = ((np.asarray(hb) > 127) | D.annulus(D.RING_IN, D.RING_OUT)) & D.circle_mask()
    g = Grb("bottom solder mask")
    emit_rings(g, D.rings_of(mask_bs, min_area_px=8))
    g.save(os.path.join(OUT, "kisara_medallion.GBS"))

    # ---------- 顶层丝印：白丝印 = 眼睛高光
    g = Grb("top silkscreen")
    emit_rings(g, silk_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTO"))

    # ---------- 底层丝印：白丝印 "KISARA"（新增）
    g = Grb("bottom silkscreen")
    tm = text_mask("KISARA", size_px=110, cy_px=int(SRC * 0.62)) & D.circle_mask()
    emit_rings(g, D.rings_of(tm, min_area_px=6))
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

    # ---------- 板框 DXF
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
