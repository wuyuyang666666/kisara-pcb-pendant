# -*- coding: utf-8 -*-
"""v12 效果图：绿阻焊 + 白丝印 + 沉金；另出 6 铜层回读拼图。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import final8 as F8
import final10 as F10
import design12 as D
import make_release12 as R12
import make_release11 as R
from verify2 import raster

GREEN, SILK_WHITE = D.GREEN, D.WHITE_SILK
GOLD, GOLD_HI = D.GOLD, D.GOLD_HI

F8.WHITE, F8.INK = GREEN, SILK_WHITE
F8.GOLD, F8.GOLD_HI = GOLD, GOLD_HI
F10.WHITE, F10.INK = GREEN, SILK_WHITE
F10.GOLD, F10.GOLD_HI = GOLD, GOLD_HI


def sheet(f, b):
    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 58
    im = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(im)
    im.paste(f, (pad, pad + 46))
    im.paste(b, (pad * 2 + f.width, pad + 46))
    d.text((pad, 18),
           "KISARA  PENDANT  v12   D56.0 mm   6 LAYER   ENIG 1U", fill=(58, 56, 52))
    d.text((pad, 34),
           "GREEN solder mask + WHITE silkscreen + gold accents  /  6L ENIG coupon compliant",
           fill=(96, 94, 90))
    d.text((pad, pad + 46 + f.height + 10),
           "FRONT   white face + green outlines, gold eyes, pleated skirt restored",
           fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10),
           "BACK    gold ring / X ornament / layered type / white dot line", fill=(96, 94, 90))
    out = os.path.join(D.ROOT, "assets", "final_v12.png")
    im.save(out)
    print("saved", out)


def copper_grid(ppm=6, tile=300):
    names = [("GTL", "L1  concentric relief"), ("G2", "L2  radial spokes"),
             ("G3", "L3  concentric + hub"), ("G4", "L4  diamond ring"),
             ("G5", "L5  dot-square array"), ("GBL", "L6  relief + bosses")]
    cols, rows = 3, 2
    pad, head = 18, 30
    W = cols * (tile + pad) + pad
    H = rows * (tile + head + pad) + pad
    out = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(out)
    for i, (name, note) in enumerate(names):
        img, _ = raster(os.path.join(R.OUT, f"kisara_medallion.{name}"), ppm=ppm)
        g = img.convert("L").resize((tile, tile), Image.LANCZOS)
        cx = pad + (i % cols) * (tile + pad)
        cy = pad + (i // cols) * (tile + head + pad)
        t = Image.new("RGB", (tile, tile), (26, 30, 28))
        t.paste((206, 203, 190), mask=g)
        out.paste(t, (cx, cy + head))
        d.text((cx, cy + 6), f"{name}   {note}", fill=(58, 56, 52))
    p = os.path.join(D.ROOT, "assets", "v12_copper_layers.png")
    out.save(p)
    print("saved", p)


def compare_v11_v12():
    """v11 / v12 正面并排，突出裙子修复。"""
    a = Image.open(os.path.join(D.ROOT, "assets", "final_v11.png")).convert("RGB")
    b = Image.open(os.path.join(D.ROOT, "assets", "final_v12.png")).convert("RGB")
    ha = a.crop((0, 0, a.width // 2, a.height))
    hb = b.crop((0, 0, b.width // 2, b.height))
    canvas = Image.new("RGB", (ha.width + hb.width + 30, max(ha.height, hb.height)),
                       (238, 236, 230))
    canvas.paste(ha, (0, 0))
    canvas.paste(hb, (ha.width + 30, 0))
    p = os.path.join(D.ROOT, "assets", "compare_v11_v12_skirt.png")
    canvas.save(p)
    print("saved", p)


def main():
    m = D.front_masks()
    sheet(F8.front(m, 22), F10.back_v10(22))
    copper_grid()
    compare_v11_v12()


if __name__ == "__main__":
    main()
