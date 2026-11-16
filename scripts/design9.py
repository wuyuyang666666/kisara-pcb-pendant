# -*- coding: utf-8 -*-
"""
木更 · 圆形挂件 v9 —— 排版加强版

用户反馈 v8「人物周边空余太多」，给了一枚吧唧徽章做排版参考：
人物几乎占满圆、头脚贴边，剩余空隙被同心圆弧、菱形串、四角星、
气泡环、散点填满（图片仅供排版参考，配色/工艺/角色都不照搬）。

做法：
  1. 角色高度 FIT_H 从 0.76 提到 0.90，头顶/鞋接近金环内边
  2. 装饰画在整圆上，再用「人物实体」掩膜裁掉压到人物的部分
     -> 装饰自然只剩人物周围的月牙形空隙，和参考图里被人物遮挡的效果一致
  3. 装饰主体走黑丝印，约 1/5 走沉金，保持 v8「少金点睛」的比例

工艺仍是：白阻焊留白 + 黑丝印 GTO + 沉金开窗 GTS；6 层 + 沉金不变。
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import design8 as D8
import bmp, morph
from design8 import *       # noqa: 复用板框/坐标/预览/实物色等全部接口

# 覆盖 v8 的构图参数（load_art 在 design8 模块内读取全局 FIT_H）
D8.FIT_H = 0.90
FIT_H = 0.90
CHAR_GAP = 0.45        # 人物与金环之间的缝
DEC_GAP = 0.25         # 装饰与金环之间的安全距


def L(mm):
    """mm -> px"""
    return mm / SCALE


def P(xmm, ymm):
    """mm 坐标 -> 位图像素坐标（y 向下）"""
    return (SRC / 2 + xmm / SCALE, SRC / 2 - ymm / SCALE)


def char_solid_mask(ink, mag):
    """人物实体：从边界对空白泛洪，未被墨线围住的都是背景"""
    solid = ink | mag
    passable = ~morph.grow(solid, 1.0)
    h, w = passable.shape
    seeds = ([(x, 0) for x in range(0, w, 3)] +
             [(x, h - 1) for x in range(0, w, 3)] +
             [(0, y) for y in range(0, h, 3)] +
             [(w - 1, y) for y in range(0, h, 3)])
    bg = bmp.flood(passable, seeds)
    return ~bg


def decorations(char_solid, ink, mag):
    """返回 (装饰黑丝印, 装饰沉金)。均只保留人物之外的圆内区域。"""
    di = Image.new("L", (SRC, SRC), 0)
    dg = Image.new("L", (SRC, SRC), 0)
    a, b = ImageDraw.Draw(di), ImageDraw.Draw(dg)

    # --- 1) 同心圆弧：被人物遮挡后变成两侧的弧段（参考图的水印同心圆）
    for rr, wmm in ((22.4, 0.26), (24.3, 0.22)):
        x0, y0 = P(-rr, rr)
        x1, y1 = P(rr, -rr)
        a.ellipse([x0, y0, x1, y1], outline=255,
                  width=max(1, int(round(L(wmm)))))

    # --- 2) 沿圆周的菱形串（参考图圆边那串斜方块）
    for i in range(24):
        ang = 2 * math.pi * i / 24 + 0.13
        rr = 24.9
        px, py = P(rr * math.cos(ang), rr * math.sin(ang))
        s = L(0.68 if i % 3 else 0.92)
        d = b if i % 4 == 0 else a
        d.polygon([(px, py - s), (px + s * 0.72, py),
                   (px, py + s), (px - s * 0.72, py)], fill=255)

    # --- 3) 四角星闪光
    def star(d, xmm, ymm, rmm, k=0.26):
        px, py = P(xmm, ymm)
        r = L(rmm)
        pts = []
        for i in range(8):
            ang = 2 * math.pi * i / 8 - math.pi / 2
            q = r if i % 2 == 0 else r * k
            pts.append((px + q * math.cos(ang), py + q * math.sin(ang)))
        d.polygon(pts, fill=255)

    stars = [(-21.5, 12.5, 1.5), (-22.6, -8.0, 1.15), (-19.5, -17.0, 0.9),
             (21.5, 14.0, 1.6), (22.4, -6.5, 1.2), (19.8, -16.5, 0.95),
             (-13.5, 21.5, 1.0), (14.0, 21.0, 0.85)]
    for i, (x, y, r) in enumerate(stars):
        star(b if i in (1, 4) else a, x, y, r)

    # --- 4) 气泡空心环
    for x, y, r in ((-20.0, 3.0, 1.6), (20.5, 1.0, 1.9),
                    (-16.5, -20.0, 1.2), (16.0, -19.5, 1.3)):
        px, py = P(x, y)
        s = L(r)
        a.ellipse([px - s, py - s, px + s, py + s], outline=255,
                  width=max(1, int(round(L(0.28)))))

    # --- 5) 散点底纹（确定性伪随机，避免像规则网格）
    rng = random.Random(7)
    for _ in range(52):
        ang = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(18.0, 25.2)
        px, py = P(rr * math.cos(ang), rr * math.sin(ang))
        s = L(rng.uniform(0.22, 0.42))
        (b if rng.random() < 0.18 else a).ellipse(
            [px - s, py - s, px + s, py + s], fill=255)

    # --- 6) 两道流星短线
    for x, y in ((-20.5, 17.0), (21.0, 9.5)):
        px, py = P(x, y)
        a.line([(px, py), (px + L(2.2), py - L(2.6))], fill=255,
               width=max(1, int(round(L(0.28)))))

    # --- 裁掉压到人物的部分，并限制在金环以内
    inner = (radius_map() < RING_IN - DEC_GAP) & circle_mask()
    keepout = morph.grow(char_solid | ink | mag, 2.0)
    doi = (np.asarray(di) > 127) & inner & ~keepout
    dog = (np.asarray(dg) > 127) & inner & ~keepout
    dog &= ~morph.grow(doi, 1.0)        # 金装饰避开黑装饰
    return doi, dog


def build_masks():
    ink, mag = D8.load_art()
    circ = circle_mask()
    R = radius_map()
    inner = (R < RING_IN - CHAR_GAP) & circ
    ring = annulus(RING_IN, RING_OUT) & circ

    cs = char_solid_mask(ink, mag)
    di, dg = decorations(cs, ink, mag)

    gold = (mag & inner) | ring | dg
    keepout = (morph.grow(mag, 1.0) |
               annulus(RING_IN - 0.35, RING_OUT + 0.35) | dg)
    silk = (ink & inner & ~keepout) | di

    return {
        "silk": silk,
        "gold": gold,
        "ring": ring,
        "ink": ink,
        "mag": mag,
        "deco": di | dg,
    }


def main():
    m = build_masks()
    mm2 = SCALE * SCALE
    print("gold=%.1f mm2  silk=%.1f mm2  deco=%.1f mm2" %
          (m["gold"].sum() * mm2, m["silk"].sum() * mm2, m["deco"].sum() * mm2))
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v9.png"))


if __name__ == "__main__":
    main()
