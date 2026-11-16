# -*- coding: utf-8 -*-
"""v11 预演：仅把工艺配色换成「绿阻焊 + 白丝印 + 沉金」，构图与 v10 完全一致。

用于让用户先确认视觉让步是否可接受，再决定是否重做生产文件。
不写任何 Gerber，只出 PNG。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import final8 as F8
import final10 as F10
import design9 as D

# 嘉立创常规绿油（深绿）+ 白色字符 + 哑光沉金
GREEN = (24, 106, 72)
SILK_WHITE = (240, 240, 234)
GOLD = (191, 160, 96)
GOLD_HI = (222, 196, 138)

# final8.front / board_layer 用模块级常量
F8.WHITE = GREEN
F8.INK = SILK_WHITE
F8.GOLD, F8.GOLD_HI = GOLD, GOLD_HI
# final10.back_v10 用自己模块内的常量副本
F10.WHITE, F10.INK = GREEN, SILK_WHITE
F10.GOLD, F10.GOLD_HI = GOLD, GOLD_HI


def sheet(f, b, title, subtitle, out):
    pad = 26
    W = f.width + b.width + pad * 3
    H = f.height + pad * 3 + 58
    im = Image.new("RGB", (W, H), (238, 236, 230))
    d = ImageDraw.Draw(im)
    im.paste(f, (pad, pad + 46))
    im.paste(b, (pad * 2 + f.width, pad + 46))
    d.text((pad, 18), title, fill=(58, 56, 52))
    d.text((pad, 34), subtitle, fill=(96, 94, 90))
    d.text((pad, pad + 46 + f.height + 10),
           "FRONT   v10 layout, green mask + white silk + gold eyes", fill=(96, 94, 90))
    d.text((pad * 2 + f.width, pad + 46 + b.height + 10),
           "BACK   v10 layout, gold ring/type + white dot line", fill=(96, 94, 90))
    im.save(out)
    print("saved", out)


def main():
    m = D.build_masks()
    f, b = F8.front(m, 22), F10.back_v10(22)
    sheet(f, b,
          "KISARA  PENDANT  v11  D56.0 mm  6 LAYER  ENIG 1U",
          "GREEN solder mask + WHITE silkscreen + gold (ENIG) accents  /  6L free-coupon compliant",
          os.path.join(D.ROOT, "assets", "preview_v11_green.png"))

    # 与 v10 正面并排对比（v10 用原色重新渲染）
    F8.WHITE, F8.INK = D.WHITE, D.INK
    F8.GOLD, F8.GOLD_HI = D.GOLD, D.GOLD_HI
    old = F8.front(m, 26)
    F8.WHITE, F8.INK = GREEN, SILK_WHITE
    F8.GOLD, F8.GOLD_HI = GOLD, GOLD_HI
    new = F8.front(m, 26)
    gap, top, bot = 30, 62, 34
    cmp = Image.new("RGB", (old.width * 2 + gap * 3, old.height + top + bot), (238, 236, 230))
    cd = ImageDraw.Draw(cmp)
    cmp.paste(old, (gap, top))
    cmp.paste(new, (gap * 2 + old.width, top))
    cd.text((gap, 20), "v10  white mask + black silk  (cannot use coupon)", fill=(58, 56, 52))
    cd.text((gap * 2 + old.width, 20), "v11  GREEN mask + WHITE silk  (coupon compliant)", fill=(58, 56, 52))
    cd.text((gap, 38), "same artwork / same gold accents / same layout", fill=(96, 94, 90))
    cd.text((gap * 2 + old.width, 38), "only process colors changed", fill=(96, 94, 90))
    out2 = os.path.join(D.ROOT, "assets", "compare_v10_v11_front.png")
    cmp.save(out2)
    print("saved", out2)


if __name__ == "__main__":
    main()
