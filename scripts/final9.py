# -*- coding: utf-8 -*-
"""v9 最终效果图：复用 v8 的渲染，替换设计模块与输出文件名。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import final8 as F
import design9 as D

F.D = D


def main():
    m = D.build_masks()
    f, b = F.front(m, 22), F.back(22)
    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 58
    sheet = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(sheet)
    sheet.paste(f, (pad, pad + 46))
    sheet.paste(b, (pad * 2 + f.width, pad + 46))
    d.text((pad, 18), "KISARA  PENDANT   D56.0 mm   6 LAYER   ENIG 1U", fill=(58, 56, 52))
    d.text((pad, 34), "white solder mask + black silkscreen + gold (ENIG) accents", fill=(96, 94, 90))
    d.text((pad, pad + 46 + f.height + 10),
           "FRONT   full-bleed chibi + badge ornaments", fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10),
           "BACK   gold ring + KISARA", fill=(96, 94, 90))
    out = os.path.join(D.ROOT, "assets", "final_v9.png")
    sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
