# -*- coding: utf-8 -*-
"""
实物色模拟：把渲染用的"理想色"换成嘉立创实际工艺色，并叠加板边/丝印/沉金的工艺特征。

参考色值（视觉采样，非官方色卡）：
  沉金 ENIG（1U" 金，镍层 3~6μm）
      主色 #B99B5E 左右——香槟金，偏灰绿，**不是亮黄**
      高光 #DBBE85，暗部 #8A7141，表面哑光磨砂，几乎无镜面反射
  哑光黑阻焊（油墨）
      主色 #26262A，强光下泛灰到 #35353A，有细颗粒
  FR4 铣边侧壁
      米黄 #C9BE9A——异形板铣完后板边必然露出的基材本色
  白色丝印
      #EEEAE0，偏暖，大面积实印会略透底，边缘比矢量图软
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import design5 as D

ROOT = D.ROOT
PPM = 24

IDEAL = dict(
    bg=(236, 234, 228),
    mask=(20, 20, 23),
    silk=(241, 241, 237),
    gold=(198, 157, 78),
    gold_hi=(240, 212, 156),
    edge=None,
)

REAL = dict(
    bg=(234, 232, 226),
    mask=(38, 38, 42),
    silk=(238, 234, 223),
    gold=(185, 155, 94),
    gold_hi=(206, 180, 124),
    edge=(201, 190, 154),          # FR4 侧壁
)


def canvas():
    W = int((D.D_BOARD + 18) * PPM)
    H = int((D.D_BOARD + D.TAB_H + 20) * PPM)
    cx, cy = W / 2, H - (D.D_BOARD / 2 + 10) * PPM
    return W, H, cx, cy


def board_masks(W, H, cx, cy):
    poly = D.board_outline()
    poly_m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(poly_m).polygon([(cx + x * PPM, cy - y * PPM) for x, y in poly], fill=255)
    # 连续两次 3x3 内缩 ≈ 2px 宽的一圈，用来表现铣边露出的 FR4 侧壁
    inner = poly_m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MinFilter(3))
    wall = np.clip(np.asarray(poly_m, np.int16) - np.asarray(inner, np.int16), 0, 255)
    return poly_m, wall.astype(np.uint8)


def layer_bitmap(mask, W, H, cx, cy):
    size = int(round(D.D_BOARD * PPM))
    im = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    im = im.resize((size, size), Image.LANCZOS)
    mk = Image.new("L", (W, H), 0)
    mk.paste(im, (int(cx - size / 2), int(cy - size / 2)))
    return mk


def render(masks, pal, textured):
    W, H, cx, cy = canvas()
    img = Image.new("RGB", (W, H), pal["bg"])
    poly_m, wall = board_masks(W, H, cx, cy)

    # 板面：阻焊色
    board = Image.new("RGB", (W, H), pal["mask"])
    img = Image.composite(board, img, poly_m)

    # 丝印
    sk = layer_bitmap(masks["silk"], W, H, cx, cy)
    if textured:
        sk = sk.filter(ImageFilter.GaussianBlur(PPM * 0.012))
    img = Image.composite(Image.new("RGB", (W, H), pal["silk"]), img,
                          sk.point(lambda v: 255 if v > 128 else 0))

    # 沉金
    gd = layer_bitmap(masks["gold"], W, H, cx, cy)
    gm = gd.point(lambda v: 255 if v > 128 else 0)
    img = Image.composite(Image.new("RGB", (W, H), pal["gold"]), img, gm)

    # 金的高光：理想版强、实物版弱且散
    if textured:
        blur = gm.filter(ImageFilter.GaussianBlur(PPM * 0.10)).point(lambda v: int(v * 0.22))
    else:
        blur = gm.filter(ImageFilter.GaussianBlur(PPM * 0.12)).point(lambda v: int(v * 0.40))
    img = Image.composite(Image.new("RGB", (W, H), pal["gold_hi"]), img, blur)

    # 板边 FR4 侧壁（仅实物版）
    if pal["edge"]:
        wm = Image.fromarray(wall.astype(np.uint8), "L")
        img = Image.composite(Image.new("RGB", (W, H), pal["edge"]), img,
                              wm.point(lambda v: int(v * 0.85)))

    # 哑光面细颗粒（仅实物版）
    if textured:
        rng = np.random.default_rng(7)
        a = np.asarray(img, np.float32)
        n = rng.normal(0, 3.2, a.shape[:2])[:, :, None]
        pm = (np.asarray(poly_m, np.float32) / 255.0)[:, :, None]
        a = np.clip(a + n * pm, 0, 255)
        img = Image.fromarray(a.astype(np.uint8))

    # 挂孔
    hx, hy, hd = D.hole()
    d = ImageDraw.Draw(img)
    r = hd / 2 * PPM
    d.ellipse([cx + hx * PPM - r, cy - hy * PPM - r,
               cx + hx * PPM + r, cy - hy * PPM + r],
              fill=pal["edge"] or (150, 148, 142))
    return img


def main():
    m = D.build_masks()
    a = render(m, IDEAL, textured=False)
    b = render(m, REAL, textured=True)

    pad = 28
    sheet = Image.new("RGB", (a.width + b.width + pad * 3, max(a.height, b.height) + pad * 3 + 46),
                      (230, 228, 222))
    d = ImageDraw.Draw(sheet)
    sheet.paste(a, (pad, pad + 42))
    sheet.paste(b, (pad * 2 + a.width, pad + 42))
    d.text((pad, 18), "IDEAL RENDER", fill=(70, 68, 64))
    d.text((pad * 2 + a.width, 18), "REAL MATERIALS  (ENIG / matte black / white silk / FR4 edge)",
           fill=(70, 68, 64))
    out = os.path.join(ROOT, "assets", "realcolor_compare.png")
    sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
