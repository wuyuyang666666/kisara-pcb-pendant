# -*- coding: utf-8 -*-
"""v12 裙子修复预览：A 绿裙+白褶线 / B 白裙+绿褶线（+鞋补白）

v11 缺陷：原稿的黑色百褶裙在「绿油+白丝印」里被当成不印（绿油留白），
裙子里的白色褶线又被 clean_silk 开运算删掉，导致裙子/鞋整块融进绿底。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design8 as D8
import design9 as D9
import design11 as D11
import bmp, morph

ROOT = D8.ROOT
SRC, SCALE = D8.SRC, D8.SCALE


def lower_roi():
    Y, X = np.ogrid[:SRC, :SRC]
    return ((Y >= 680) & (Y <= 915) & (X >= 340) & (X <= 690) &
            (D8.radius_map() < D8.RING_IN - D9.CHAR_GAP) & D8.circle_mask())


def patch_A(ink, mag, cs, roi):
    """绿裙 + 白褶线：把原稿下半身的白色细节加粗补回白丝印。
    排除超大连通域（那是背景白），只留褶线/裙摆边/袜子这类中小块。
    鞋子是纯黑块面、没有白色细节可补，单独把它的块面填白；
    与袜子之间靠原稿那条黑色横线（此处为绿油）自然分隔。"""
    white = (~ink & ~mag) & cs & roi
    keep = np.zeros_like(white)
    for a, reg in bmp.components(white, min_area=12):
        if a < 20000:
            keep |= reg
    lines = morph.grow(keep, 1.0)

    Y = np.arange(SRC)[:, None]
    big = morph.grow(morph.shrink(ink, 3.0), 3.0)
    shoes = big & cs & roi & (Y >= 852) & ~morph.grow(mag, 1.0)
    # 只描鞋的下半圈轮廓，不填白：填白会让袜子+鞋连成白柱，反而更糟
    edge = shoes & ~morph.shrink(shoes, 2.5)
    edge = morph.grow(edge & (Y >= 866), 1.0)
    return lines | edge


def patch_B(ink, mag, cs, roi):
    """白裙 + 绿褶线：大块黑色面反转成白丝印，再挖 5 条绿色褶线。
    用圆盘腐蚀+膨胀挑出「大块面」，细黑线不会被误填。"""
    big = morph.grow(morph.shrink(ink, 3.0), 3.0)
    patch = big & cs & roi & ~morph.grow(mag, 1.0)

    # 百褶裙褶线（缩放后坐标）：从腰线向裙摆放射，宽 4px = 0.219mm
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    for xt, xb in ((430, 390), (470, 452), (512, 512), (555, 572), (595, 634)):
        d.line([(xt, 708), (xb, 812)], fill=255, width=4)
    # 鞋与袜之间一道绿线，避免两条腿连成白柱
    d.line([(405, 872), (475, 872)], fill=255, width=4)
    d.line([(550, 872), (620, 872)], fill=255, width=4)
    pleats = np.asarray(img) > 127
    return patch & ~pleats


def compose(base, patch):
    m = dict(base)
    m["silk"] = (base["silk"] | patch) & ~morph.grow(base["gold"], 1.0)
    m["patch"] = patch
    return m


def main():
    ink, mag = D8.load_art()
    cs = D9.char_solid_mask(ink, mag)
    roi = lower_roi()
    base = D11.front_masks()
    area = np.pi * (D8.D_BOARD / 2) ** 2

    outs = {}
    for tag, fn in (("A", patch_A), ("B", patch_B)):
        p = fn(ink, mag, cs, roi)
        m = compose(base, p)
        st = morph.stroke_width(m["silk"], 1 / SCALE)
        print("%s: patch=%6d px (%.1f mm2)  silk=%.1f mm2 (%.1f%%)  "
              "P5=%.3fmm  <0.155mm=%.1f%%" %
              (tag, p.sum(), p.sum() * SCALE**2,
               m["silk"].sum() * SCALE**2,
               100 * m["silk"].sum() * SCALE**2 / area,
               st["p5"], 100 * st["frac_under"]))
        path = os.path.join(ROOT, "assets", "try_skirt_%s.png" % tag)
        D8.preview(m, ppm=16, path=path)
        outs[tag] = Image.open(path).convert("RGB")
        Image.fromarray((m["silk"] * 255).astype("uint8"), "L").save(
            os.path.join(ROOT, "assets", "try_skirt_%s_GTO.png" % tag))

    a, b = outs["A"], outs["B"]
    canvas = Image.new("RGB", (a.width + b.width + 30, max(a.height, b.height)), (245, 245, 245))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + 30, 0))
    canvas.save(os.path.join(ROOT, "assets", "compare_skirt_AB.png"))
    print("saved compare_skirt_AB.png")


if __name__ == "__main__":
    main()
