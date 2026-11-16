# -*- coding: utf-8 -*-
"""v8 最终效果图：正面白底黑线金点睛 / 背面金环金字 / 实物色"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
import design8 as D
from make_release8 import bottom_gold_mask

ROOT = D.ROOT
BG, WHITE, INK = D.BG, D.WHITE, D.INK
GOLD, GOLD_HI, FR4 = D.GOLD, D.GOLD_HI, D.FR4


def canvas(ppm):
    W = int((D.D_BOARD + 18) * ppm)
    H = int((D.D_BOARD + D.TAB_H + 20) * ppm)
    cx, cy = W / 2, H - (D.D_BOARD / 2 + 10) * ppm
    return W, H, cx, cy


def board_layer(W, H, cx, cy, ppm):
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon(
        [(cx + x * ppm, cy - y * ppm) for x, y in D.board_outline()], fill=255)
    img = Image.new("RGB", (W, H), BG)
    sh = bm.filter(ImageFilter.GaussianBlur(ppm * 0.45))
    img = Image.composite(Image.new("RGB", (W, H), (70, 68, 64)), img,
                          sh.point(lambda v: int(v * 0.24)))
    img = Image.composite(Image.new("RGB", (W, H), WHITE), img, bm)
    return img, bm


def blit(W, H, cx, cy, ppm, mask):
    size = int(round(D.D_BOARD * ppm))
    im = Image.fromarray(mask.astype("uint8") * 255, "L").resize((size, size), Image.LANCZOS)
    mk = Image.new("L", (W, H), 0)
    mk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
    return mk.point(lambda v: 255 if v > 120 else 0)


def punch(img, cx, cy, ppm):
    hx, hy, hd = D.hole()
    r = hd / 2 * ppm
    ImageDraw.Draw(img).ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                                 cx + hx * ppm + r, cy - hy * ppm + r], fill=FR4)
    return img


def front(masks, ppm=22):
    W, H, cx, cy = canvas(ppm)
    img, _ = board_layer(W, H, cx, cy, ppm)
    gm = blit(W, H, cx, cy, ppm, masks["gold"])
    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, gm)
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.filter(ImageFilter.GaussianBlur(ppm * 0.08))
                            .point(lambda v: int(v * 0.16)))
    img = Image.composite(Image.new("RGB", (W, H), INK), img,
                          blit(W, H, cx, cy, ppm, masks["silk"]))
    return punch(img, cx, cy, ppm)


def back(ppm=22):
    W, H, cx, cy = canvas(ppm)
    img, _ = board_layer(W, H, cx, cy, ppm)
    gm = blit(W, H, cx, cy, ppm, bottom_gold_mask())
    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, gm)
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.filter(ImageFilter.GaussianBlur(ppm * 0.08))
                            .point(lambda v: int(v * 0.16)))
    return punch(img, cx, cy, ppm)


def main():
    m = D.build_masks()
    f, b = front(m, 22), back(22)
    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 58
    sheet = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(sheet)
    sheet.paste(f, (pad, pad + 46))
    sheet.paste(b, (pad * 2 + f.width, pad + 46))
    d.text((pad, 18), "KISARA  PENDANT   D56.0 mm   6 LAYER   ENIG 1U", fill=(58, 56, 52))
    d.text((pad, 34), "white solder mask + black silkscreen + gold (ENIG) accents", fill=(96, 94, 90))
    d.text((pad, pad + 46 + f.height + 10), "FRONT   chibi Kisara / gold eyes", fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10),
           "BACK   gold ring + KISARA", fill=(96, 94, 90))
    out = os.path.join(ROOT, "assets", "final_v8.png")
    sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
