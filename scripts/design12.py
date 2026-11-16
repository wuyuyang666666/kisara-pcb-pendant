# -*- coding: utf-8 -*-
"""木更 · 圆形挂件 v12 —— 修复 v11 的「裙子消失」缺陷，其余与 v11 完全一致。

v11 缺陷根因：原稿的百褶裙/鞋是纯黑块面 + 白色褶线。
换成「绿阻焊 + 白丝印」的 B 方案后：
  黑色块面 -> 不印 = 绿油留白（与背景同色，整块融掉）
  裙内白色褶线 -> 被 clean_silk 的开运算当细条删掉
结果裙子与鞋完全不可见，只剩两条白袜子悬空。

v12 修复（方案 A，绿裙 + 白褶线，最忠实原稿且白丝印增量最小）：
  1. 从原稿下半身取白色细节（褶线/裙摆边/袜子），排除背景大块，加粗补回白丝印
  2. 鞋子是纯黑块面无白色细节，只描下半圈白色外轮廓；填白会让袜+鞋连成白柱
  3. 其余（沉金、背面、6 层铜、板框、钻孔）全部沿用 v11，一字不改

券条件不变：绿油 / 白字 / 沉金 1U / 6 层 / 1.6mm / 5 片 / 单片 / 无阻抗。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design8 as D8
import design9 as D9
import design11 as D11
from design11 import *          # noqa: 配色 + design8 的全部接口给 make_release12 复用
import bmp, morph

SRC, SCALE = D8.SRC, D8.SCALE


def lower_roi():
    """下半身 ROI（缩放后的 1024 图坐标），限定在人物可印圆内。"""
    Y, X = np.ogrid[:SRC, :SRC]
    return ((Y >= 680) & (Y <= 915) & (X >= 340) & (X <= 690) &
            (D8.radius_map() < D8.RING_IN - D9.CHAR_GAP) & D8.circle_mask())


def skirt_patch():
    """要补进 GTO 白丝印的裙子/鞋细节。"""
    ink, mag = D8.load_art()
    cs = D9.char_solid_mask(ink, mag)
    roi = lower_roi()

    # 1) 原稿下半身的白色细节：排除超大连通域（背景白），保留褶线/裙摆边/袜子
    white = (~ink & ~mag) & cs & roi
    keep = np.zeros_like(white)
    for a, reg in bmp.components(white, min_area=12):
        if a < 20000:
            keep |= reg
    lines = morph.grow(keep, 1.0)

    # 2) 鞋：只描下半圈白色外轮廓，不填白
    Y = np.arange(SRC)[:, None]
    big = morph.grow(morph.shrink(ink, 3.0), 3.0)
    shoes = big & cs & roi & (Y >= 852) & ~morph.grow(mag, 1.0)
    edge = shoes & ~morph.shrink(shoes, 2.5)
    edge = morph.grow(edge & (Y >= 866), 1.0)
    return lines | edge


def front_masks():
    m = dict(D11.front_masks())
    p = skirt_patch()
    m["silk"] = (m["silk"] | p) & ~morph.grow(m["gold"], 1.0)
    m["skirt_patch"] = p
    return m


def build_masks():
    return front_masks()


def back_gold_mask():
    return D11.back_gold_mask()


def back_silk_mask():
    return D11.back_silk_mask()


def main():
    m = front_masks()
    mm2 = SCALE * SCALE
    area = np.pi * (D_BOARD / 2) ** 2
    st = morph.stroke_width(m["silk"], 1 / SCALE)
    print("FRONT white silk = %.1f mm2 (%.1f%%)  gold = %.1f mm2 (%.1f%%)" %
          (m["silk"].sum() * mm2, 100 * m["silk"].sum() * mm2 / area,
           m["gold"].sum() * mm2, 100 * m["gold"].sum() * mm2 / area))
    print("skirt patch = %.1f mm2   silk P5=%.3fmm  <0.155mm=%.1f%%" %
          (m["skirt_patch"].sum() * mm2, st["p5"], 100 * st["frac_under"]))
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v12.png"))


if __name__ == "__main__":
    main()
