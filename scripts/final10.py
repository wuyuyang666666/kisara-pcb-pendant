# -*- coding: utf-8 -*-
"""v10 效果图：正面沿用 v9，背面换成 back10 新版式；另出一张 v9/v10 背面对比图。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
import final8 as F
import design9 as D
import back10 as B

F.D = D
BG, WHITE, INK = D.BG, D.WHITE, D.INK
GOLD, GOLD_HI = D.GOLD, D.GOLD_HI


def back_v10(ppm=22):
    """背面：白阻焊 + 沉金（金环/X发饰/字组）+ 黑丝印细点线"""
    W, H, cx, cy = F.canvas(ppm)
    img, _ = F.board_layer(W, H, cx, cy, ppm)
    gm = F.blit(W, H, cx, cy, ppm, B.bottom_gold_mask())
    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, gm)
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.filter(ImageFilter.GaussianBlur(ppm * 0.08))
                            .point(lambda v: int(v * 0.16)))
    img = Image.composite(Image.new("RGB", (W, H), INK), img,
                          F.blit(W, H, cx, cy, ppm, B.bottom_silk_mask()))
    return F.punch(img, cx, cy, ppm)


def main():
    m = D.build_masks()
    f, b = F.front(m, 22), back_v10(22)
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
           "FRONT   v9 unchanged - full-bleed chibi + ornaments", fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10),
           "BACK   v10 - ring / dot line / X ornament / layered type", fill=(96, 94, 90))
    out = os.path.join(D.ROOT, "assets", "final_v10.png")
    sheet.save(out)
    print("saved", out)

    # ---- 背面对比图：v9 旧版 vs v10 新版
    old, new = F.back(26), back_v10(26)
    gap, top, bot = 30, 62, 34
    cw = old.width + new.width + gap * 3
    ch = old.height + top + bot
    cmp = Image.new("RGB", (cw, ch), (238, 236, 230))
    cd = ImageDraw.Draw(cmp)
    cmp.paste(old, (gap, top))
    cmp.paste(new, (gap * 2 + old.width, top))
    cd.text((gap, 20), "BACK SIDE  -  v9  (before)", fill=(58, 56, 52))
    cd.text((gap, 36), "gold ring + KISARA / ENGAGE KISS only", fill=(96, 94, 90))
    cd.text((gap * 2 + old.width, 20), "BACK SIDE  -  v10  (after)", fill=(58, 56, 52))
    cd.text((gap * 2 + old.width, 36),
            "+ dot line / X ornament / divider / 6L ENIG imprint", fill=(96, 94, 90))
    out2 = os.path.join(D.ROOT, "assets", "back_v9_vs_v10.png")
    cmp.save(out2)
    print("saved", out2)


if __name__ == "__main__":
    main()
