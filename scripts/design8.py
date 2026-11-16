# -*- coding: utf-8 -*-
"""
木更 · 圆形挂件 v8 —— 白阻焊 + 黑丝印块面/勾线 + 沉金点睛

参考「怪盗基德」PCB 挂件的高还原度与「白为主 + 深色块面 + 少量金」的配色方向，
但比例按木更自身特征来（红瞳是最大识别点，所以金点睛面积比基德大）。

输入：三色分区版画稿（纯白 / 纯黑 / 品红 #FF00FF），Q版2头身全身。
映射：
    纯白  -> 白色阻焊留白（不印，天然均匀，占最大面积）
    纯黑  -> 黑色丝印 GTO（粗勾线 + 头发暗部、百褶裙、鞋等块面）
    品红  -> 沉金开窗 GTS（红瞳→金瞳、领结、菱形、腮红、袜口）
    外圈  -> 沉金金环
    背面  -> 沉金金环 + 沉金 "KISARA" 字

为什么不做 v7 那种大面积金像：参考板是白占大头，深色是勾线/块面，
金只做点睛；且白色用阻焊本身表达最均匀，不会触碰
「阻焊 10~15um > 丝印 5~8um，薄墨盖大面积必发花」这条红线
（本版黑丝印只占约 1/4 板面，且白阻焊+黑丝印是嘉立创的合法硬配对）。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import bmp
import edge as E
import lineart as LA
import morph

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Convert_the_anime_girl_in_imag_2026-11-06T09-23-41.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
EDGE_MARGIN = 0.35

SRC = 1024
SCALE = D_BOARD / SRC

RING_IN, RING_OUT = 26.3, 27.2   # 沉金外圈（宽 0.9mm）
CHAR_GAP = 0.7                   # 角色与金环之间的白缝（mm）
FIT_H = 0.76                     # 角色高度占板径比例（全身竖构图，留圆内边距）

# 实物色
BG = (230, 228, 222)      # 板外画布
WHITE = (246, 245, 240)   # 白色阻焊
INK = (24, 25, 28)        # 黑色丝印
GOLD = (191, 160, 96)     # 沉金（哑光香槟金）
GOLD_HI = (222, 196, 138)
FR4 = (201, 190, 154)


# ---------------------------------------------------------------- 板框

def board_outline(n_arc=260):
    R = D_BOARD / 2
    hw = TAB_W / 2.0
    y_j = math.sqrt(R * R - hw * hw)
    cap_cy = R + TAB_H - hw
    a0 = math.atan2(y_j, -hw)
    a1 = math.atan2(y_j, hw) + 2 * math.pi
    pts = [(R * math.cos(a0 + (a1 - a0) * i / n_arc),
            R * math.sin(a0 + (a1 - a0) * i / n_arc)) for i in range(n_arc + 1)]
    pts.append((hw, cap_cy))
    for i in range(1, 25):
        a = math.pi * i / 24
        pts.append((hw * math.cos(a), cap_cy + hw * math.sin(a)))
    pts.append((-hw, cap_cy))
    pts.append((-hw, y_j))
    return pts


def hole():
    return (0.0, D_BOARD / 2 + TAB_H - TAB_W / 2.0, HOLE_D)


def mp(px, py):
    return ((px - SRC / 2) * SCALE, (SRC / 2 - py) * SCALE)


def circle_mask(margin=EDGE_MARGIN):
    yy, xx = np.mgrid[0:SRC, 0:SRC]
    mx = (xx + 0.5 - SRC / 2) * SCALE
    my = (SRC / 2 - (yy + 0.5)) * SCALE
    r = D_BOARD / 2 - margin
    return mx * mx + my * my < r * r


def radius_map():
    yy, xx = np.mgrid[0:SRC, 0:SRC]
    mx = (xx + 0.5 - SRC / 2) * SCALE
    my = (SRC / 2 - (yy + 0.5)) * SCALE
    return np.sqrt(mx * mx + my * my)


def annulus(r_in, r_out):
    R = radius_map()
    return (R >= r_in) & (R < r_out)


# ---------------------------------------------------------------- 三色分区

def classify(img):
    """纯白 / 纯黑 / 品红 -> (ink, magenta) 两张布尔图"""
    a = np.asarray(img.convert("RGB")).astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = (r * 299 + g * 587 + b * 114) // 1000
    # 品红 #FF00FF：R、B 高，G 低；也吃掉抗锯齿的浅粉边缘
    mag = (r > 120) & (b > 100) & (g < r * 0.62) & (g < b * 0.72) & ((r - g) > 70)
    ink = (lum < 130) & ~mag
    return ink, mag


def keep_components(mask, min_area):
    out = np.zeros_like(mask)
    for a, r in bmp.components(mask, min_area=min_area):
        out |= r
    return out


def load_art():
    """裁白边 -> 按高度缩放到圆内 -> 返回 (ink, magenta) 两张 SRC 方图"""
    img = Image.open(LIN).convert("RGB")
    ink, mag = classify(img)
    W, H = img.size
    nz = ink | mag
    ys, xs = np.nonzero(nz)
    if not len(xs):
        raise RuntimeError("三色稿为空")
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = int(0.02 * max(W, H))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(W, x1 + pad), min(H, y1 + pad)
    cw, ch = x1 - x0, y1 - y0
    th = int(SRC * FIT_H)
    tw = max(1, int(round(th * cw / ch)))

    def rz(m):
        im = Image.fromarray(m[y0:y1, x0:x1].astype(np.uint8) * 255, "L")
        return np.asarray(im.resize((tw, th), Image.LANCZOS)) > 127

    i2, m2 = rz(ink), rz(mag)
    m2 = keep_components(m2, 24)          # 滤掉抗锯齿碎点（保留腮红短线）
    i2 = keep_components(i2 & ~m2, 12)    # 品红优先，黑线避让
    i2 = morph.grow(i2, 0.6)              # 补闭合缺口 + 保证丝印线宽
    i2 = i2 & ~m2                         # grow 后再避让一次

    def paste(m):
        c = np.zeros((SRC, SRC), dtype=bool)
        ox, oy = (SRC - tw) // 2, (SRC - th) // 2
        c[oy:oy + th, ox:ox + tw] = m
        return c

    return paste(i2), paste(m2)


def build_masks():
    ink, mag = load_art()
    circ = circle_mask()
    R = radius_map()
    inner = (R < RING_IN - CHAR_GAP) & circ
    ring = annulus(RING_IN, RING_OUT) & circ

    # 沉金开窗 = 品红点睛 + 外圈金环（品红内部的白色高光点自动成为阻焊白点）
    gold = (mag & inner) | ring

    # 黑丝印 = 黑线/块面，避开金面 1px（防板厂裁丝印）与金环
    keepout = morph.grow(mag, 1.0) | annulus(RING_IN - 0.35, RING_OUT + 0.35)
    silk = ink & inner & ~keepout

    return {
        "silk": silk,        # 黑色丝印 GTO
        "gold": gold,        # 沉金开窗 GTS
        "ring": ring,
        "ink": ink,
        "mag": mag,
    }


# ---------------------------------------------------------------- 位图 -> 多边形

def rings_of(mask, eps=0.06, min_area_px=10):
    out = []
    for r in E.rings(mask):
        if abs(E.area(r)) < min_area_px:
            continue
        pts = LA.rdp([mp(x, y) for x, y in r], eps)
        if len(pts) >= 3:
            out.append(pts)
    return out


def preview(masks, ppm=16, path=None):
    W = int((D_BOARD + 18) * ppm)
    H = int((D_BOARD + TAB_H + 20) * ppm)
    img = Image.new("RGB", (W, H), BG)
    cx, cy = W / 2, H - (D_BOARD / 2 + 10) * ppm

    def T(x, y):
        return (cx + x * ppm, cy - y * ppm)

    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon([T(x, y) for x, y in board_outline()], fill=255)
    img = Image.composite(Image.new("RGB", (W, H), WHITE), img, bm)

    size = int(round(D_BOARD * ppm))
    ox, oy = int(cx - size / 2), int(cy - size / 2)

    def blit(mask):
        im = Image.fromarray(mask.astype(np.uint8) * 255, "L").resize((size, size), Image.LANCZOS)
        mk = Image.new("L", (W, H), 0)
        mk.paste(im, (ox, oy))
        return mk.point(lambda v: 255 if v > 128 else 0)

    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, blit(masks["gold"]))
    img = Image.composite(Image.new("RGB", (W, H), INK), img, blit(masks["silk"]))

    hx, hy, hd = hole()
    r = hd / 2 * ppm
    ImageDraw.Draw(img).ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                                 cx + hx * ppm + r, cy - hy * ppm + r],
                                fill=FR4)
    if path:
        img.save(path)
    return img


def main():
    m = build_masks()
    mm2 = SCALE * SCALE
    print("gold=%dpx (%.1f mm2)  silk=%dpx (%.1f mm2)" %
          (m["gold"].sum(), m["gold"].sum() * mm2,
           m["silk"].sum(), m["silk"].sum() * mm2))
    print("board area = %.1f mm2" % (math.pi * (D_BOARD / 2) ** 2))
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v8.png"))


if __name__ == "__main__":
    main()
