# -*- coding: utf-8 -*-
"""
木更 · 圆形挂件 v10 —— 背面版式（正面完全沿用 v9，不碰）

设计判断：翻面时视觉密度落差过大（正面 22% 黑 + 8% 金，背面白 > 95%），
需要「补完成度，不补密度」。参考收藏章/挑战币背面惯例：

  1. 金环保留 —— 两面呼应的锚点，翻面时轮廓连续
  2. 内侧一圈黑丝印细点线 —— 比正面同心圆弧更细更疏，边缘有完成度
  3. KISARA 上方一对极简 X 形交叉发饰（沉金）—— 呼应角色标识，比再放一张脸高级
  4. 字组做层次：粗体 KISARA / 短分隔线 + 双菱形 / ENGAGE KISS / 极小 6L · ENIG 落款
  5. 中央保持大面积白阻焊留白 —— 对比度本身就是设计，也留出手写签名的余地

工艺不增加任何新工序：仍是白阻焊 + 黑丝印 + 沉金，下单参数一个字不改。
GBO 从 v9 的空文件变成「细点线」，仍是白阻焊/黑丝印合法硬配对，且避开所有金面。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import design9 as D

ROOT, SRC, SCALE = D.ROOT, D.SRC, D.SCALE

FONTS = [
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\bahnschrift.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
]

# 版式坐标（mm，圆心为原点，y 向上）
Y_XORN = 11.2          # 双 X 发饰中心
Y_MAIN = 3.0           # KISARA
Y_DIV = -1.9           # 分隔线 / 双菱形
Y_SUB = -5.4           # ENGAGE KISS
Y_FOOT = -10.6         # 6L · ENIG
R_DOTS = 24.9          # 内侧细点线半径（金环内边 26.3，留 1.4mm 安全距）
N_DOTS = 72


def L(mm):
    """mm -> px"""
    return mm / SCALE


def P(xmm, ymm):
    """mm 坐标 -> 位图像素坐标（y 向下）"""
    return (SRC / 2 + xmm / SCALE, SRC / 2 - ymm / SCALE)


def load_font(size_px):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size_px)
    return ImageFont.load_default()


def text_mask(text, size_px, ymm):
    """居中排一行字，ymm 为字形包围盒中心的 mm 坐标"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    font = load_font(size_px)
    bb = d.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    x = (SRC - w) / 2 - bb[0]
    cy = SRC / 2 - ymm / SCALE
    y = cy - (bb[1] + bb[3]) / 2
    d.text((x, y), text, font=font, fill=255)
    return np.asarray(img) > 127


def x_ornament():
    """一对 X 形交叉发饰 —— 木更最简的标识符号"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    w = max(1, int(round(L(0.64))))
    hx, hy = L(1.72), L(1.42)
    for xmm in (-2.9, 2.9):
        cx, cy = P(xmm, Y_XORN)
        d.line([(cx - hx, cy - hy), (cx + hx, cy + hy)], fill=255, width=w)
        d.line([(cx - hx, cy + hy), (cx + hx, cy - hy)], fill=255, width=w)
    return np.asarray(img) > 127


def divider():
    """主字与副标题之间的短分隔线 + 两端小菱形"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    cx, cy = P(0, Y_DIV)
    hw, t = L(5.0), max(1, int(round(L(0.30))))
    d.rectangle([cx - hw, cy - t / 2, cx + hw, cy + t / 2], fill=255)
    s = L(0.66)
    for xmm in (-6.3, 6.3):
        px, py = P(xmm, Y_DIV)
        d.polygon([(px, py - s), (px + s * 0.78, py),
                   (px, py + s), (px - s * 0.78, py)], fill=255)
    return np.asarray(img) > 127


def foot_rule():
    """工艺落款两侧的极细短线"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    t = max(1, int(round(L(0.20))))
    for x0, x1 in ((-8.6, -5.4), (5.4, 8.6)):
        a, b = P(x0, Y_FOOT), P(x1, Y_FOOT)
        d.line([(a[0], a[1]), (b[0], b[1])], fill=255, width=t)
    return np.asarray(img) > 127


def dot_ring():
    """内侧黑丝印细点线：比正面同心圆弧更细更疏；每 6 点一个刻度点"""
    img = Image.new("L", (SRC, SRC), 0)
    d = ImageDraw.Draw(img)
    for i in range(N_DOTS):
        ang = 2 * math.pi * i / N_DOTS
        px, py = P(R_DOTS * math.cos(ang), R_DOTS * math.sin(ang))
        s = L(0.30 if i % 6 == 0 else 0.19)
        d.ellipse([px - s, py - s, px + s, py + s], fill=255)
    return np.asarray(img) > 127


def bottom_gold_mask():
    """GBS 沉金开窗：金环 + 双 X 发饰 + 字组层次"""
    ring = D.annulus(D.RING_IN, D.RING_OUT)
    g = (ring | x_ornament() |
         text_mask("KISARA", 104, Y_MAIN) |
         divider() |
         text_mask("ENGAGE KISS", 40, Y_SUB) |
         text_mask("6L  ·  ENIG", 26, Y_FOOT) |
         foot_rule())
    return g & D.circle_mask()


def bottom_silk_mask():
    """GBO 黑丝印：仅一圈内侧细点线，避开所有金面"""
    return dot_ring() & D.circle_mask()


def main():
    g, s = bottom_gold_mask(), bottom_silk_mask()
    a = math.pi * (D.D_BOARD / 2) ** 2
    print("BACK gold = %.1f mm2 (%.1f%%)   silk = %.1f mm2 (%.1f%%)   white = %.1f%%" %
          (g.sum() * SCALE ** 2, 100 * g.sum() * SCALE ** 2 / a,
           s.sum() * SCALE ** 2, 100 * s.sum() * SCALE ** 2 / a,
           100 * (a - g.sum() * SCALE ** 2 - s.sum() * SCALE ** 2) / a))
    # 检查黑丝印与金面是否冲突
    import morph
    ov = (s & morph.grow(g, 1.0)).sum()
    print("silk-on-gold overlap = %d px (should be 0)" % ov)


if __name__ == "__main__":
    main()
