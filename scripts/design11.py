# -*- coding: utf-8 -*-
"""
木更 · 圆形挂件 v11 —— 为「6层沉金EDA专用券」重做（第一目标：通过券审核）

券的硬性条件（嘉立创帮助文档 37576 / 37593）：
  真 6 层、<=10x10cm、1.6mm、5片、绿油、单片出货、沉金、无阻抗、
  常规工艺、文件 100% 由嘉立创 EDA 设计、沉金面积 < 20%、小助手/移动端下单。

本模块负责「工艺可行」的部分：
  阻焊 白 -> 绿；丝印 黑 -> 白；沉金保留；角色与背面版式沿用 v9/v10。

视觉方案 B（用户选定）：
  角色内部的白区（脸/水手服/袜子/亮发）改成【白色丝印块面】，
  墨线与暗部不印、露出绿色阻焊当勾线，背景与装饰仍是绿底白线。
  -> 换绿油后仍是「白脸木更」，不像 A 方案那样变成绿脸负片。

「EDA 血统」不是脚本能解决的，需按 README_v11 的步骤在嘉立创 EDA 内
导入并另存工程后下单；本模块只保证交付的 Gerber 本身合规。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import design8 as D8
import design9 as D9
import back10 as B10
import bmp, morph
from design8 import *       # noqa: 导出板框/坐标/环/预览等全部接口给 make_release11

# 工艺配色（绿油 + 白字 + 哑光沉金）；只影响渲染，不影响掩膜
GREEN = (24, 106, 72)
WHITE_SILK = (240, 240, 234)
GOLD = (191, 160, 96)
GOLD_HI = (222, 196, 138)
# 覆盖 from design8 import * 带进来的旧配色，让复用脚本取到的也是绿油白字
WHITE, INK = GREEN, WHITE_SILK
D8.WHITE, D8.INK = GREEN, WHITE_SILK
D8.GOLD, D8.GOLD_HI = GOLD, GOLD_HI


def clean_silk(silk, r_px=1.5):
    """圆盘开运算：去掉宽度 < 3px (0.164mm) 的细白条/孤立碎点。

    B 方案把「角色实体 - 墨线」当白丝印时，发丝之间会留下 2px 宽的窄白缝，
    实测 12.7% 的脊线低于 0.155mm 丝印下限，实物会断线或被板厂 DFM 裁掉。
    开运算只削掉这些细缝，白脸/水手服等大块面保形不变。
    """
    core = morph.shrink(silk, r_px)
    return morph.grow(core, r_px) & silk


def front_masks():
    """正面：B 方案的白丝印 + 沿用 v9 的沉金区"""
    m = D9.build_masks()
    ink, mag = D8.load_art()
    cs = D9.char_solid_mask(ink, mag)
    R = D8.radius_map()
    inner = (R < D8.RING_IN - D9.CHAR_GAP) & D8.circle_mask()

    # 角色实体的「白区」= 实体 - 墨线 - 金区 - 金环安全距
    char_white = (cs & inner & ~morph.grow(ink | mag, 1.0) &
                  ~D8.annulus(D8.RING_IN - 0.35, D8.RING_OUT + 0.35))
    # 装饰的黑部分仍走白丝印；金装饰与金环保持在 gold 里
    _, dg = D9.decorations(cs, ink, mag)
    deco_white = m["deco"] & ~dg

    silk = (char_white | deco_white) & ~morph.grow(m["gold"], 1.0)
    silk = clean_silk(silk)
    return {
        "silk": silk,           # GTO 白色丝印
        "gold": m["gold"],      # GTS 沉金开窗（含金环）
        "ring": m["ring"],
        "ink": ink,
        "mag": mag,
        "deco": deco_white,
    }


def back_gold_mask():
    """GBS 背面沉金：v10 版式原样保留"""
    return B10.bottom_gold_mask()


def back_silk_mask():
    """GBO 背面白色丝印：v10 的内侧细点线（掩膜不变，颜色由黑改白）"""
    return B10.bottom_silk_mask()


def build_masks():
    """给渲染/复用脚本用的统一入口（正面）"""
    return front_masks()


def main():
    m = front_masks()
    mm2 = SCALE * SCALE
    area = np.pi * (D_BOARD / 2) ** 2
    print("FRONT white silk = %.1f mm2 (%.1f%%)  gold = %.1f mm2 (%.1f%%)  green = %.1f%%" %
          (m["silk"].sum() * mm2, 100 * m["silk"].sum() * mm2 / area,
           m["gold"].sum() * mm2, 100 * m["gold"].sum() * mm2 / area,
           100 * (area - m["silk"].sum() * mm2 - m["gold"].sum() * mm2) / area))
    bg, bs = back_gold_mask(), back_silk_mask()
    print("BACK  white silk = %.1f mm2 (%.1f%%)  gold = %.1f mm2 (%.1f%%)" %
          (bs.sum() * mm2, 100 * bs.sum() * mm2 / area,
           bg.sum() * mm2, 100 * bg.sum() * mm2 / area))
    print("gold both sides = %.1f mm2 = %.1f%% of one board face (coupon limit 20%%)" %
          ((m["gold"].sum() + bg.sum()) * mm2,
           100 * (m["gold"].sum() + bg.sum()) * mm2 / area))
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v11.png"))


if __name__ == "__main__":
    main()
