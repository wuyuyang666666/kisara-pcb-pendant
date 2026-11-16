# -*- coding: utf-8 -*-
"""v7 最终效果图：正面金像 / 背面金心+KISARA / 实物色"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import design7 as D
from make_release7 import heart_poly, text_mask, load_font

ROOT = D.ROOT
BG = D.BG
MASK_C = D.MASK_C
SILK = D.SILK
GOLD = D.GOLD
GOLD_HI = D.GOLD_HI
FR4 = (201, 190, 154)


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
    img = Image.composite(Image.new("RGB", (W, H), (30, 30, 32)), img,
                          sh.point(lambda v: int(v * 0.30)))
    img = Image.composite(Image.new("RGB", (W, H), MASK_C), img, bm)
    return img, bm


def blit(W, H, cx, cy, ppm, mask):
    size = int(round(D.D_BOARD * ppm))
    im = Image.fromarray(mask.astype("uint8") * 255, "L").resize((size, size), Image.LANCZOS)
    mk = Image.new("L", (W, H), 0)
    mk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
    return mk.point(lambda v: 255 if v > 120 else 0)


def front(masks, ppm=22, real=True):
    W, H, cx, cy = canvas(ppm)
    img, bm = board_layer(W, H, cx, cy, ppm)
    img = Image.composite(Image.new("RGB", (W, H), GOLD), img,
                          blit(W, H, cx, cy, ppm, masks["gold"]))
    img = Image.composite(Image.new("RGB", (W, H), SILK), img,
                          blit(W, H, cx, cy, ppm, masks["silk"]))
    gm = blit(W, H, cx, cy, ppm, masks["gold"]).filter(ImageFilter.GaussianBlur(ppm * 0.08))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.point(lambda v: int(v * (0.18 if real else 0.35))))
    return punch(img, cx, cy, ppm)


def back(ppm=22, real=True):
    W, H, cx, cy = canvas(ppm)
    img, bm = board_layer(W, H, cx, cy, ppm)
    hp = heart_poly(0, 0.5, 8.2)
    lay = Image.new("L", (W, H), 0)
    ImageDraw.Draw(lay).polygon([(cx + x * ppm, cy - y * ppm) for x, y in hp], fill=255)
    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, lay)
    # 金环
    rz = int((D.RING_IN + D.RING_OUT) / 2 * ppm)
    rwid = int((D.RING_OUT - D.RING_IN) * ppm)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - rz, cy - rz, cx + rz, cy + rz], outline=GOLD, width=rwid)
    # 白丝印 KISARA
    tm = text_mask("KISARA", size_px=110, cy_px=int(D.SRC * 0.62))
    img = Image.composite(Image.new("RGB", (W, H), SILK), img,
                          blit(W, H, cx, cy, ppm, tm))
    gm = lay.filter(ImageFilter.GaussianBlur(ppm * 0.10))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.point(lambda v: int(v * (0.18 if real else 0.35))))
    return punch(img, cx, cy, ppm)


def punch(img, cx, cy, ppm):
    hx, hy, hd = D.hole()
    r = hd / 2 * ppm
    ImageDraw.Draw(img).ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                                 cx + hx * ppm + r, cy - hy * ppm + r], fill=FR4)
    return img


def main():
    m = D.build_masks()
    f = front(m, 22, real=True)
    b = back(22, real=True)

    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 58
    sheet = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(sheet)
    sheet.paste(f, (pad, pad + 46))
    sheet.paste(b, (pad * 2 + f.width, pad + 46))
    d.text((pad, 18), "KISARA  PENDANT   D56.0 mm   6 LAYER   ENIG 1U", fill=(58, 56, 52))
    d.text((pad, 34), "black solder mask + gold (ENIG) + white silkscreen", fill=(96, 94, 90))
    d.text((pad, pad + 46 + f.height + 10), "FRONT   gold chibi portrait", fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10), "BACK   gold heart + KISARA", fill=(96, 94, 90))
    out = os.path.join(ROOT, "assets", "final_v7.png")
    sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
