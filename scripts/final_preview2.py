# -*- coding: utf-8 -*-
"""生成正反面成品效果图（用于展示与下单参考）"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
import design5 as D
from make_release import heart_poly

ROOT = D.ROOT
BG = (206, 204, 198)
MASK_C = (20, 20, 23)
GOLD = (198, 157, 78)
GOLD_HI = (240, 212, 156)
SILK = (241, 241, 237)


def canvas(ppm=18):
    W = int((D.D_BOARD + 18) * ppm)
    H = int((D.D_BOARD + D.TAB_H + 20) * ppm)
    cx, cy = W / 2, H - (D.D_BOARD / 2 + 10) * ppm
    return W, H, cx, cy


def frame(W, H, cx, cy, ppm, poly, bg=BG):
    img = Image.new("RGB", (W, H), bg)
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon([(cx + x * ppm, cy - y * ppm) for x, y in poly], fill=255)
    sh = bm.filter(ImageFilter.GaussianBlur(ppm * 0.55))
    img = Image.composite(Image.new("RGB", (W, H), (150, 148, 142)), img,
                          sh.point(lambda v: int(v * 0.45)))
    return img, bm


def front(masks, ppm=20):
    W, H, cx, cy = canvas(ppm)
    img, bm = frame(W, H, cx, cy, ppm, D.board_outline())

    size = int(round(D.D_BOARD * ppm))
    layer = Image.new("RGB", (W, H), MASK_C)
    for key, color in (("gold", GOLD), ("clear", MASK_C), ("silk", SILK)):
        im = Image.fromarray(masks[key].astype("uint8") * 255, "L")
        im = im.resize((size, size), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
        mk = Image.new("L", (W, H), 0)
        mk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
        layer = Image.composite(Image.new("RGB", (W, H), color), layer, mk)

    img = Image.composite(layer, img, bm)

    # 沉金高光
    im = Image.fromarray(masks["gold"].astype("uint8") * 255, "L").resize((size, size), Image.LANCZOS)
    mk = Image.new("L", (W, H), 0)
    mk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
    mk = mk.filter(ImageFilter.GaussianBlur(ppm * 0.12))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          mk.point(lambda v: int(v * 0.40)))
    return img, (W, H, cx, cy)


def back(ppm=20):
    W, H, cx, cy = canvas(ppm)
    img, bm = frame(W, H, cx, cy, ppm, D.board_outline())
    layer = Image.new("RGB", (W, H), MASK_C)
    d = ImageDraw.Draw(layer)
    hp = heart_poly(0, 1.0, 7.2)
    d.polygon([(cx + x * ppm, cy - y * ppm) for x, y in hp], fill=GOLD)
    img = Image.composite(layer, img, bm)
    mk = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mk).polygon([(cx + x * ppm, cy - y * ppm) for x, y in hp], fill=255)
    mk = mk.filter(ImageFilter.GaussianBlur(ppm * 0.14))
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          mk.point(lambda v: int(v * 0.42)))
    return img, (W, H, cx, cy)


def punch_hole(img, geo, ppm):
    W, H, cx, cy = geo
    hx, hy, hd = D.hole()
    r = hd / 2 * ppm
    d = ImageDraw.Draw(img)
    d.ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
               cx + hx * ppm + r, cy - hy * ppm + r], fill=BG)
    return img


def main():
    m = D.build_masks()
    f, gf = front(m, 20)
    b, gb = back(20)
    f = punch_hole(f, gf, 20)
    b = punch_hole(b, gb, 20)

    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 54
    sheet = Image.new("RGB", (W, H), (236, 234, 228))
    d = ImageDraw.Draw(sheet)
    sheet.paste(f, (pad, pad + 44))
    sheet.paste(b, (pad * 2 + f.width, pad + 44))
    d.text((pad, 20), "KISARA  MEDALLION   d56.0 mm   6L ENIG   matte black + white silk",
           fill=(60, 58, 54))
    d.text((pad, pad + 44 + f.height + 8), "FRONT  (gold iris + black pupil)", fill=(90, 88, 84))
    d.text((pad * 2 + f.width, pad + 44 + b.height + 8), "BACK  (gold heart)", fill=(90, 88, 84))
    out = os.path.join(ROOT, "assets", "final_medallion.png")
    sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
