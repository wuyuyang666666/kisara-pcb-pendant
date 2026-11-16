# -*- coding: utf-8 -*-
"""按图层模型渲染实物效果图（黑阻焊 + 沉金 + 白丝印）"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
import design2 as D

ROOT = D.ROOT
BG = (208, 206, 200)
MASK = (22, 22, 25)
MASK_HI = (46, 46, 50)
GOLD = (198, 158, 84)
GOLD_HI = (236, 206, 148)
SILK = (240, 240, 236)


def render(d, ppm=16, path=None, back=False):
    W = int((D.D_BOARD + 18) * ppm)
    H = int((D.D_BOARD + D.TAB_H + 20) * ppm)
    cx, cy = W / 2, H - (D.D_BOARD / 2 + 10) * ppm

    def T(x, y):
        return (cx + x * ppm, cy - y * ppm)

    img = Image.new("RGB", (W, H), BG)
    d0 = ImageDraw.Draw(img)
    # 背景细微渐变
    for i in range(H):
        k = 1.0 - 0.06 * abs(i / H - 0.5)
        d0.line([(0, i), (W, i)], fill=(int(BG[0] * k), int(BG[1] * k), int(BG[2] * k)))

    poly = [T(*p) for p in d["outline"]]

    # 板本体 + 边缘
    board = Image.new("L", (W, H), 0)
    ImageDraw.Draw(board).polygon(poly, fill=255)
    shadow = board.filter(ImageFilter.GaussianBlur(ppm * 0.6))
    img = Image.composite(Image.new("RGB", (W, H), (150, 148, 142)), img,
                          shadow.point(lambda v: int(v * 0.45)))

    layer = Image.new("RGB", (W, H), MASK)
    dl = ImageDraw.Draw(layer)

    if back:
        # 背面：只放一颗小爱心 + 一圈金环
        pass
    else:
        for g in d["gold_fill"]:
            dl.polygon([T(*p) for p in g], fill=GOLD)
        for pts, w in d["gold_stroke"]:
            dl.line([T(*p) for p in pts], fill=GOLD, width=max(1, int(w * ppm)),
                    joint="curve")
        for g in d["mask_clear"]:
            dl.polygon([T(*p) for p in g], fill=MASK)
        for pts, w in d["silk"]:
            if len(pts) < 2:
                continue
            dl.line([T(*p) for p in pts], fill=SILK,
                    width=max(1, int(round(w * ppm))), joint="curve")
        for g in d.get("silk_fill", []):
            dl.polygon([T(*p) for p in g], fill=SILK)

    img = Image.composite(layer, img, board)

    # 沉金高光
    gm = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(gm)
    for g in d["gold_fill"]:
        gd.polygon([T(*p) for p in g], fill=255)
    for pts, w in d["gold_stroke"]:
        gd.line([T(*p) for p in pts], fill=255, width=max(1, int(w * ppm)))
    gm = gm.filter(ImageFilter.GaussianBlur(ppm * 0.10))
    gm = Image.composite(gm, Image.new("L", (W, H), 0), board)
    img = Image.composite(Image.new("RGB", (W, H), GOLD_HI), img,
                          gm.point(lambda v: int(v * 0.38)))

    # 挂孔
    hx, hy, hd = d["hole"]
    r = hd / 2 * ppm
    dd = ImageDraw.Draw(img)
    dd.ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                cx + hx * ppm + r, cy - hy * ppm + r], fill=BG)
    dd.arc([cx + hx * ppm - r, cy - hy * ppm - r,
            cx + hx * ppm + r, cy - hy * ppm + r], 200, 20, fill=(120, 118, 112))

    if path:
        img.save(path)
    return img


def main():
    d = D.build()
    out = os.path.join(ROOT, "assets", "medallion_v2.png")
    render(d, ppm=16, path=out)
    print("saved", out)


if __name__ == "__main__":
    main()
