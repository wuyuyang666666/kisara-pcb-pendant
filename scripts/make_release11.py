# -*- coding: utf-8 -*-
"""v11 生产文件：绿阻焊 + 白丝印 + 沉金，6 个铜层各有不同真实图形。

输出 build/gerber11/，不覆盖 v8/v9/v10 的 Gerber。
  GTS = 正面沉金开窗      GTO = 正面白色丝印
  GBS = 背面沉金开窗      GBO = 背面白色丝印
  6 铜层 = 整板铺铜 + 各层专属「挖空」图案（emit_rings 按嵌套深度自动 LPC 挖空）

重要：GTL/GBL 的挖空必须避开两面的沉金开窗区 —— 沉金只沉积在铜上，
开窗下面没有铜会镀不上。内层 G2~G5 不参与沉金，图案自由。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design11 as D
import design8 as D8
import bmp, morph
from grb import Grb, emit_rings

ROOT = D.ROOT
OUT = os.path.join(ROOT, "build", "gerber11")
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


def P(xmm, ymm):
    return (SRC / 2 + xmm / SCALE, SRC / 2 - ymm / SCALE)


def L(mm):
    return mm / SCALE


def W(mm):
    """图案线宽：至少 2px (0.109mm)，高于券要求的 0.09mm 线宽线隙"""
    return max(2, int(round(L(mm))))


def carve_pattern(idx):
    """第 idx 个铜层要挖掉的图案（布尔图）。各层互不相同，全部限制在 R<24mm。"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)

    def ring(rr, wmm=0.35):
        x0, y0 = P(-rr, rr)
        x1, y1 = P(rr, -rr)
        d.ellipse([x0, y0, x1, y1], outline=255, width=W(wmm))

    def diamond(x, y, s_mm):
        px, py = P(x, y)
        s = L(s_mm)
        d.polygon([(px, py - s), (px + s * 0.72, py),
                   (px, py + s), (px - s * 0.72, py)], fill=255)

    if idx == 0:            # L1 顶层：两道同心细环（避开正面金区）
        ring(16.5, 0.35)
        ring(21.0, 0.35)
    elif idx == 1:          # L2：24 条放射短线
        for i in range(24):
            a = 2 * math.pi * i / 24
            d.line([P(11 * math.cos(a), 11 * math.sin(a)),
                    P(22.5 * math.cos(a), 22.5 * math.sin(a))],
                   fill=255, width=W(0.35))
    elif idx == 2:          # L3：三道同心圆 + 中心实心圆
        ring(8.5, 0.32)
        ring(14.0, 0.32)
        ring(19.5, 0.32)
        cx, cy = P(0, 0)
        s = L(2.6)
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=255)
    elif idx == 3:          # L4：圆周菱形串 28 枚
        for i in range(28):
            a = 2 * math.pi * i / 28
            diamond(17.5 * math.cos(a), 17.5 * math.sin(a), 1.15)
    elif idx == 4:          # L5：散点方块阵列（互不相连，避免复杂嵌套）
        for x in (-15, -10, -5, 0, 5, 10, 15):
            for y in (-15, -10, -5, 0, 5, 10, 15):
                if x * x + y * y > 22.5 ** 2:
                    continue
                px, py = P(x, y)
                s = L(0.85)
                d.rectangle([px - s, py - s, px + s, py + s], fill=255)
    else:                   # L6 底层：两道不同半径环 + 四角小圆（避开背面金区）
        ring(12.5, 0.35)
        ring(21.5, 0.35)
        for x, y in ((-8, 8), (8, 8), (-8, -8), (8, -8)):
            px, py = P(x, y)
            s = L(1.5)
            d.ellipse([px - s, py - s, px + s, py + s], fill=255)

    arr = np.asarray(img) > 127
    return arr & (D.radius_map() < 24.0)


def copper_mask(idx, surface_gold):
    base = holes_bitmap(board_bitmap(0.25), D.HOLE_D / 2 + 0.9)
    carve = carve_pattern(idx)
    if idx in (0, 5):
        # 沉金开窗下方必须有铜，挖空图案避开该面的全部金区
        carve = carve & ~morph.grow(surface_gold, 4.0)
    return base & ~carve


def write_dxf(poly, path, layer="OUTLINE"):
    Ls = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
          "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES",
          "0", "LWPOLYLINE", "8", layer, "90", str(len(poly)), "70", "1"]
    for x, y in poly:
        Ls += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    Ls += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(Ls))


def main():
    os.makedirs(OUT, exist_ok=True)
    m = D.front_masks()
    bg, bs = D.back_gold_mask(), D.back_silk_mask()
    print("FRONT silk %.1fmm2 gold %.1fmm2 | BACK silk %.1fmm2 gold %.1fmm2" %
          (m["silk"].sum() * SCALE ** 2, m["gold"].sum() * SCALE ** 2,
           bs.sum() * SCALE ** 2, bg.sum() * SCALE ** 2))

    fg_rings = D.rings_of(m["gold"], eps=0.05, min_area_px=8)
    fs_rings = D.rings_of(m["silk"], eps=0.07, min_area_px=10)
    bg_rings = D.rings_of(bg, eps=0.05, min_area_px=8)
    bs_rings = D.rings_of(bs, eps=0.035, min_area_px=6)
    print("rings: GTS=%d GTO=%d GBS=%d GBO=%d" %
          (len(fg_rings), len(fs_rings), len(bg_rings), len(bs_rings)))

    layers = [
        ("GTL", "L1 top copper / concentric relief", m["gold"]),
        ("G2", "L2 inner copper / 24 radial spokes", None),
        ("G3", "L3 inner copper / concentric circles + hub", None),
        ("G4", "L4 inner copper / 28 diamond ring", None),
        ("G5", "L5 inner copper / dot-square array", None),
        ("GBL", "L6 bottom copper / relief + corner bosses", bg),
    ]
    for idx, (name, note, surf) in enumerate(layers):
        cm = copper_mask(idx, surf if surf is not None else np.zeros_like(m["gold"]))
        rings = D.rings_of(cm, eps=0.10, min_area_px=12)
        g = Grb(note)
        emit_rings(g, rings)
        g.save(os.path.join(OUT, f"kisara_medallion.{name}"))
        print("  %-4s copper %.1f%%  carved %.1fmm2  rings=%d" %
              (name, 100 * cm.sum() / board_bitmap(0.0).sum(),
               (~cm & (D.radius_map() < 24.0)).sum() * SCALE ** 2, len(rings)))

    g = Grb("top solder mask opening / ENIG")
    emit_rings(g, fg_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTS"))

    g = Grb("bottom solder mask opening / ENIG")
    emit_rings(g, bg_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBS"))

    g = Grb("top silkscreen / WHITE")
    emit_rings(g, fs_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GTO"))

    g = Grb("bottom silkscreen / WHITE dot ring")
    emit_rings(g, bs_rings)
    g.save(os.path.join(OUT, "kisara_medallion.GBO"))

    outline = D.board_outline()
    g = Grb("board outline")
    g.path(outline + [outline[0]], 0.10)
    g.save(os.path.join(OUT, "kisara_medallion.GKO"))

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
