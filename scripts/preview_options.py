# -*- coding: utf-8 -*-
"""v11 两个视觉方案预演（都满足绿油 + 白字 + 沉金）：

A 纯换色：绿阻焊留白 + 白丝印线条，角色呈「绿底白线」负片感，零改动最快。
B 保白脸：角色实体内部改成白丝印块面，墨线/暗部露绿作勾线，
          背景与装饰仍是绿底白线 —— 更接近原作「白脸粉发」的神态。

只出 PNG，不写 Gerber。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design8 as D8
import design9 as D9
import final8 as F8
import bmp, morph

GREEN = (24, 106, 72)
SILK_WHITE = (240, 240, 234)
GOLD, GOLD_HI = (191, 160, 96), (222, 196, 138)
F8.WHITE, F8.INK = GREEN, SILK_WHITE
F8.GOLD, F8.GOLD_HI = GOLD, GOLD_HI


def masks_B():
    m = D9.build_masks()
    ink, mag = D8.load_art()
    cs = D9.char_solid_mask(ink, mag)
    R = D8.radius_map()
    inner = (R < D8.RING_IN - D9.CHAR_GAP) & D8.circle_mask()

    # 角色内部的「白区」= 实体 - 墨线 - 金区 - 金环安全距
    char_white = (cs & inner & ~morph.grow(ink | mag, 1.0) &
                  ~D8.annulus(D8.RING_IN - 0.35, D8.RING_OUT + 0.35))
    char_white = char_white & ~morph.grow(m["gold"], 1.0)

    # 装饰（黑部分）仍走白丝印；金装饰与金环不变
    _, dg = D9.decorations(cs, ink, mag)
    deco_black = m["deco"] & ~dg
    silk = char_white | deco_black
    return {"silk": silk, "gold": m["gold"]}


def main():
    mA, mB = D9.build_masks(), masks_B()
    a, b = F8.front(mA, 26), F8.front(mB, 26)
    gap, top, bot = 30, 64, 34
    im = Image.new("RGB", (a.width * 2 + gap * 3, a.height + top + bot), (238, 236, 230))
    d = ImageDraw.Draw(im)
    im.paste(a, (gap, top))
    im.paste(b, (gap * 2 + a.width, top))
    d.text((gap, 20), "OPTION A   pure recolor  (green face / white lines)", fill=(58, 56, 52))
    d.text((gap * 2 + a.width, 20), "OPTION B   white face + green outlines", fill=(58, 56, 52))
    d.text((gap, 38), "no artwork changes, fastest", fill=(96, 94, 90))
    d.text((gap * 2 + a.width, 38), "closer to original Kisara, larger white-silk area", fill=(96, 94, 90))
    out = os.path.join(D8.ROOT, "assets", "compare_v11_optionAB.png")
    im.save(out)
    print("saved", out)
    area = 3.141592653589793 * (D8.D_BOARD / 2) ** 2
    for tag, m in (("A", mA), ("B", mB)):
        s = m["silk"].sum() * D8.SCALE ** 2
        g = m["gold"].sum() * D8.SCALE ** 2
        print("%s: white silk %.1f mm2 (%.1f%%)  gold %.1f mm2 (%.1f%%)  green %.1f%%" %
              (tag, s, 100 * s / area, g, 100 * g / area, 100 * (area - s - g) / area))


if __name__ == "__main__":
    main()
