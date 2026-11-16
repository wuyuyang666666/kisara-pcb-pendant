# -*- coding: utf-8 -*-
"""
木更 · 圆形头像挂件 v7 —— 黑阻焊 + 金像 + 白丝印（参考牧濑红莉栖 PCB 挂件）

为什么要改：v6「白油黑字」虽然工艺稳，但只是黑白线稿，发色/五官层次丢失，
        辨识度不够，用户否决。参考「牧濑红莉栖」沉金挂件的做法：
          黑色阻焊作底（大面积黑无需丝印，天然均匀）
          金色沉金 = 角色主体（阻焊开窗，金属质感，最抓眼）
          白色丝印 = 眼睛高光等细节点缀（面积极小，不触碰「薄墨盖大面积必发花」红线）

层分配（v7）：
  黑色阻焊  整板覆盖（背景、线条、阴影都是它，无需 Gerber 表达）
  沉金开窗  = 角色内部白色区域（头发/脸/衣服，GTS）+ 外圈金环
  白色丝印  = 眼睛高光（GTO）
  背面      金色心形 + 金环（GBS）+ 白丝印 "KISARA"（GBO）

线稿 → 金像的映射方法（位图分区，非矢量化描线）：
  1. 灰度阈值分出「墨线」(ink) 与「空白」(white)
  2. 从图像边界对空白做泛洪，得到「背景」；其余被墨线围起来的空白 = 角色内部 → 金
  3. 墨线 = 黑（阻焊保留），背景 = 黑，角色内部 = 金
  这样得到「黑底金像、内部黑线」的版画效果，和牧濑那款一致。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import bmp
import edge as E
import lineart as LA
import morph

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Chibi_Q_version_line_art_of_Ki_2026-11-06T09-01-51.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
EDGE_MARGIN = 0.35

SRC = 1024
SCALE = D_BOARD / SRC

RING_IN, RING_OUT = 26.3, 27.2   # 沉金外圈（宽 0.9mm，贴板边）
CHAR_GAP = 0.7                   # 角色与金环之间留的黑缝（mm）

THR = 140          # 灰度阈值：< THR 视为墨线
MIN_CHAR = 220     # 角色内部连通域最小面积（px），滤掉噪点

# 实物色（黑底金像）
BG = (232, 230, 224)
MASK_C = (26, 27, 30)        # 黑阻焊
SILK = (240, 240, 244)       # 白丝印
GOLD = (192, 162, 98)
GOLD_HI = (218, 192, 134)


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


# ---------------------------------------------------------------- 线稿 → 金像

def load_ink():
    """载入线稿，裁掉四周留白并放大到满板，返回墨线布尔图"""
    img = Image.open(LIN).convert("L")
    W, H = img.size
    ink = np.asarray(img) < THR
    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        raise RuntimeError("线稿为空")
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    px, py = max(1, int(0.03 * W)), max(1, int(0.03 * H))
    x0, y0 = max(0, x0 - px), max(0, y0 - py)
    x1, y1 = min(W, x1 + px), min(H, y1 + py)
    crop = img.crop((x0, y0, x1, y1))
    s = min(SRC * 0.88 / crop.width, SRC * 0.88 / crop.height)
    nw, nh = max(1, int(crop.width * s)), max(1, int(crop.height * s))
    crop = crop.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (SRC, SRC), 255)
    canvas.paste(crop, ((SRC - nw) // 2, (SRC - nh) // 2))
    return np.asarray(canvas) < THR


def keep_components(mask, min_area):
    out = np.zeros_like(mask)
    for a, r in bmp.components(mask, min_area=min_area):
        out |= r
    return out


def find_eyes(gold):
    """在金色角色里找两只眼睛（被眼眶线围起来的独立金色连通域）"""
    comps = bmp.components(gold, min_area=30)
    eyes = []
    for a, r in comps:
        ys, xs = np.nonzero(r)
        cx = (xs.min() + xs.max()) / 2
        cy = (ys.min() + ys.max()) / 2
        w = xs.max() - xs.min()
        h = ys.max() - ys.min()
        if not (SRC * 0.30 < cx < SRC * 0.70):
            continue
        if not (SRC * 0.22 < cy < SRC * 0.58):
            continue
        if not (0.5 < w / max(h, 1) < 2.0):
            continue
        if a > 26000:          # 排除连成一片的脸+头发主体
            continue
        eyes.append((a, r, cx, cy, w, h))
    eyes.sort(key=lambda t: -t[0])
    return eyes[:2]


def add_catchlights(silk, gold, eyes):
    """白丝印眼睛高光：每只眼虹膜左上角一个小白点"""
    h, w = gold.shape
    out = silk.copy()
    for _, r, cx, cy, ew, eh in eyes:
        rr = min(ew, eh) * 0.22
        hx, hy = cx - ew * 0.22, cy - eh * 0.24
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=255)
        out |= (np.asarray(im) > 127) & gold   # 高光只落在虹膜(金)上
    return out


def build_masks():
    ink = load_ink()
    ink2 = morph.grow(ink, 1.0)        # 闭合轮廓上的小缺口
    passable = ~ink2
    h, w = ink.shape
    seeds = [(x, 0) for x in range(0, w, 3)] + [(x, h - 1) for x in range(0, w, 3)] + \
            [(0, y) for y in range(0, h, 3)] + [(w - 1, y) for y in range(0, h, 3)]
    bg = bmp.flood(passable, seeds)     # 背景 = 从边界可达的空白
    char = keep_components(passable & ~bg, min_area=MIN_CHAR)   # 角色内部 → 金

    circ = circle_mask()
    R = radius_map()
    ring = annulus(RING_IN, RING_OUT) & circ

    # 金色 = 角色内部（缩到金环内，留黑缝） + 金环
    gold = (char & (R < RING_IN - CHAR_GAP) & circ) | ring

    # 白丝印：正面留空（半眯眼自动定位不可靠，正面纯黑底金像更稳）
    # 白丝印只用在背面 "KISARA" 文字（见 make_release7.py）
    silk = np.zeros_like(gold)

    return {
        "silk": silk & circ,            # 白丝印（GTO，正面为空）
        "gold": gold & circ,            # 沉金开窗（GTS）
        "ring": ring,
        "eyes": [],
        "ink": ink,
    }


# ---------------------------------------------------------------- 位图 -> 多边形

def rings_of(mask, eps=0.05, min_area_px=15):
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
    img = Image.composite(Image.new("RGB", (W, H), MASK_C), img, bm)

    size = int(round(D_BOARD * ppm))
    ox, oy = int(cx - size / 2), int(cy - size / 2)

    def blit(mask):
        im = Image.fromarray(mask.astype(np.uint8) * 255, "L").resize((size, size), Image.LANCZOS)
        mk = Image.new("L", (W, H), 0)
        mk.paste(im, (ox, oy))
        return mk.point(lambda v: 255 if v > 128 else 0)

    img = Image.composite(Image.new("RGB", (W, H), GOLD), img, blit(masks["gold"]))
    img = Image.composite(Image.new("RGB", (W, H), SILK), img, blit(masks["silk"]))

    hx, hy, hd = hole()
    r = hd / 2 * ppm
    ImageDraw.Draw(img).ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                                 cx + hx * ppm + r, cy - hy * ppm + r],
                                fill=(198, 190, 172))
    if path:
        img.save(path)
    return img


def main():
    m = build_masks()
    print("gold px=%d  silk px=%d  eyes=%d" %
          (int(m["gold"].sum()), int(m["silk"].sum()), len(m["eyes"])))
    gold_area_mm2 = m["gold"].sum() * SCALE * SCALE
    print("gold area = %.1f mm^2 (板面积 %.1f mm^2)" % (gold_area_mm2, math.pi * (D_BOARD / 2) ** 2))
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v7.png"))


if __name__ == "__main__":
    main()
