# -*- coding: utf-8 -*-
"""生成完整生产文件：6 层 Gerber + 钻孔 + 板框 DXF/SVG + 效果图 + 打包"""
import os, sys, math, json, zipfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design6 as D
import bmp
import grb
from grb import Grb, emit_rings, ring_area

ROOT = D.ROOT
OUT = os.path.join(ROOT, "build", "gerber3")
D_BOARD = D.D_BOARD
SCALE = D.SCALE
SRC = D.SRC


# ---------------------------------------------------------------- 板框位图

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


# ---------------------------------------------------------------- 爱心（背面）

def heart_poly(cx=0.0, cy=0.0, s=8.0, n=64):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 16.0, cy + y * s / 16.0))
    return pts


# ---------------------------------------------------------------- 主流程

def main():
    os.makedirs(OUT, exist_ok=True)
    m = D.build_masks()
    print("masks ok")

    silk_rings = D.rings_of(m["silk"])
    # 阻焊开窗 = 沉金区挖掉高光小洞；嵌套关系由 emit_rings 自动判极性
    mask_ts = m["gold"] & ~m["clear"]
    gold_rings = D.rings_of(mask_ts, min_area_px=8)
    clear_rings = []
    print("rings silk=%d gold=%d" % (len(silk_rings), len(gold_rings)))

    board = board_bitmap(0.0)
    copper = board_bitmap(0.25)
    copper = holes_bitmap(copper, D.HOLE_D / 2 + 0.9)   # 钻孔外的隔离环
    cu_rings = D.rings_of(copper, eps=0.3, min_area_px=50)
    print("copper rings", len(cu_rings))

    outline = D.board_outline()
    board_poly = board_bitmap(0.0)
    board_rings = D.rings_of(board_poly, eps=0.12, min_area_px=50)

    # ---------- L1 顶层铜：整板铺铜，避免阻焊下发灰
    g = Grb("L1 top copper")
    emit_rings(g, cu_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTL"))

    # ---------- L2/L4/L5 实心平面
    for name, note in (("G2", "L2 GND plane"), ("G4", "L4 power plane"),
                       ("G5", "L5 GND plane")):
        g = Grb(note)
        emit_rings(g, cu_rings)
        g.save(os.path.join(OUT, f"kisara_medallion.{name}"))

    # ---------- L3 彩蛋层：星形 + 双环（肉眼不可见，仅供 X 光）
    g = Grb("L3 gimmick")
    emit_rings(g, cu_rings)
    star = []
    for i in range(10):
        a = math.pi / 5 * i - math.pi / 2
        r = 11.0 if i % 2 == 0 else 4.6
        star.append((r * math.cos(a), r * math.sin(a)))
    g.pol("C")
    g.region(star)
    for rr, w in ((14.0, 0.5), (15.6, 0.5)):
        g.path([(rr * math.cos(2 * math.pi * i / 72), rr * math.sin(2 * math.pi * i / 72))
                for i in range(73)], w)
    g.pol("D")
    g.save(os.path.join(OUT, "kisara_medallion.G3"))

    # ---------- L6 底层铜
    g = Grb("L6 bottom copper")
    emit_rings(g, cu_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBL"))

    # ---------- 顶层阻焊：开窗 = 沉金
    g = Grb("top solder mask")
    emit_rings(g, gold_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTS"))

    # ---------- 底层阻焊：金心 + 同款金环（与正面呼应）
    hb = Image.new("L", (SRC, SRC), 0)
    hp = heart_poly(0, 0.5, 8.2)
    ImageDraw.Draw(hb).polygon(
        [(x / SCALE + SRC / 2, SRC / 2 - y / SCALE) for x, y in hp], fill=255)
    mask_bs = ((np.asarray(hb) > 127) | D.annulus(D.RING_IN, D.RING_OUT)) & D.circle_mask()
    g = Grb("bottom solder mask")
    emit_rings(g, D.rings_of(mask_bs, min_area_px=8))
    g.save(os.path.join(OUT, "kisara_medallion.GBS"))

    # ---------- 顶层丝印
    g = Grb("top silkscreen")
    emit_rings(g, silk_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTO"))

    # ---------- 板框
    g = Grb("board outline")
    g.path(outline + [outline[0]], 0.10)
    g.save(os.path.join(OUT, "kisara_medallion.GKO"))

    # ---------- 钻孔
    hx, hy, hd = D.hole()
    with open(os.path.join(OUT, "kisara_medallion.TXT"), "w", encoding="ascii",
              newline="\n") as f:
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
