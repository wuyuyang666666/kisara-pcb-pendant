# -*- coding: utf-8 -*-
"""
木更 · 圆形头像徽章 v6  —— 白油黑字工艺版

为什么要改：v5 用「黑阻焊 + 大面积白丝印」，工艺上是错的。
  嘉立创官方数据：阻焊油厚 10~15μm，字符（丝印）油厚只有 5~8μm。
  用 5~8μm 的薄墨去覆盖 92% 的板面，必然厚薄不均、透底、发花，
  官方对“大面积不饱满”的建议原话就是“做白油黑字”。
  且白丝印只能配黑/绿阻焊，黑丝印配白阻焊——这是硬配对规则。

v6 层分配：
  白色阻焊  整板覆盖（厚、均匀、白度好，不需要 Gerber 表达）
  黑色丝印  = 线稿本身（细线，只占 8% 面积，工艺风险极低）
  沉金开窗  = 两只眼睛椭圆（GTS）
  黑丝印    = 瞳孔、高光
  背面      金色心形（GBS 开窗）+ 黑丝印描边

同时修掉 v5 的致命线宽问题：
  原线稿 26.2% 的线窄于 0.155mm（丝印能力下限），最细 0.109mm，
  照原样印会糊成一片。这里统一膨胀 1px，最小线宽抬到 0.22mm。
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import bmp
import edge as E
import lineart as LA
import morph

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
LIN = os.path.join(ROOT, "assets", "lineart_src",
                   "Convert_this_anime_illustratio_2026-11-05T15-01-23.png")

D_BOARD = 56.0
TAB_W, TAB_H = 11.0, 7.5
HOLE_D = 3.0
EDGE_MARGIN = 0.35

EYE_BOXES = [(258, 378, 432, 568), (588, 348, 758, 542)]
SRC = 1024
SCALE = D_BOARD / SRC

GROW_PX = 1.0            # 线稿膨胀量，最小线宽 0.109 -> 0.219 mm
RING_IN, RING_OUT = 26.3, 27.2   # 沉金外圈（宽 0.9mm，贴板边）

# 实物色（白油黑字）
BG = (232, 230, 224)
MASK_C = (247, 245, 239)     # 白阻焊
SILK = (32, 32, 34)          # 黑丝印
GOLD = (186, 156, 96)
GOLD_HI = (208, 182, 126)


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


# ---------------------------------------------------------------- 图层

def load_raw():
    return np.asarray(Image.open(LIN).convert("L"), np.float32) < 128


def eye_masks(raw):
    """
    眼睛 = 眼框内全部白区合并后填洞（内部睫毛/虹膜纹理被填平成一整块金色），
    眼眶线本身在眼框外，得以保留。

    返回 gold, pupil_center, pupil_r, hl_center, hl_r
    """
    white = ~raw
    gold = np.zeros_like(raw)
    eyes = []
    for x0, y0, x1, y1 in EYE_BOXES:
        sub = np.zeros_like(raw)
        sub[y0:y1, x0:x1] = True
        comps = bmp.components(white & sub, min_area=60)
        eye = None
        for a, r in comps:
            ys, xs = np.nonzero(r)
            if xs.min() > x0 + 1 and xs.max() < x1 - 1 and \
               ys.min() > y0 + 1 and ys.max() < y1 - 1:
                eye = (a, r)
                break
        if eye is None:
            continue
        a_eye, eye_r = eye
        ys, xs = np.nonzero(eye_r)
        ex0, ex1, ey0, ey1 = xs.min(), xs.max(), ys.min(), ys.max()
        # 只合并「完全落在眼框内」的白块（眼白/虹膜/瞳/高光）——
        # 贴框边的块属于脸部白区，并进来会把金面填成矩形
        region = np.zeros_like(raw)
        for a, r in comps:
            ys3, xs3 = np.nonzero(r)
            if xs3.min() > x0 + 1 and xs3.max() < x1 - 1 and \
               ys3.min() > y0 + 1 and ys3.max() < y1 - 1:
                region |= r
        region = bmp.fill_holes(region) & sub
        # 原图的虹膜纹理有开口，fill_holes 填不平，先闭运算补齐再填一次
        region = bmp.fill_holes(morph.grow(region, 2.0)) & sub
        region = morph.shrink(region, 2.0) & sub
        gold |= region

        # 瞳孔圆心取原图最暗块（pupil 面积 3%~25%）的质心，没有就用眼中心
        cx_e, cy_e = xs.mean(), ys.mean()
        pc = (cx_e, cy_e)
        best = None
        for a, r in comps:
            if a == a_eye:
                continue
            ys2, xs2 = np.nonzero(r)
            cx2, cy2 = xs2.mean(), ys2.mean()
            if ex0 < cx2 < ex1 and ey0 < cy2 < ey1 and 0.03 * a_eye < a < 0.25 * a_eye:
                if best is None or a > best[0]:
                    best = (a, cx2, cy2)
        if best:
            pc = (best[1], best[2])
        rw = (ex1 - ex0) / 2.0
        rh = (ey1 - ey0) / 2.0
        eyes.append(dict(pc=pc, r=min(rw, rh) * 0.44, box=(ex0, ey0, ex1, ey1)))
    return gold, eyes


def add_pupils(silk, gold, eyes):
    """黑色瞳孔（丝印）+ 白色高光（不开窗的小洞）"""
    h, w = silk.shape
    out = silk.copy()
    clear = np.zeros_like(gold)
    for e in eyes:
        cx, cy = e["pc"]
        r = e["r"]
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        out |= (np.asarray(im) > 127) & gold
        # 高光：瞳孔左上，白阻焊
        hr = r * 0.36
        hx, hy = cx - r * 0.30, cy - r * 0.34
        im2 = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im2).ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=255)
        clear |= (np.asarray(im2) > 127) & gold
    return out, clear


def build_masks():
    raw = load_raw()
    gold, eyes = eye_masks(raw)
    circ = circle_mask()

    # 丝印线：加粗到可印，再裁到板内
    line = morph.grow(raw & circ, GROW_PX) & circ
    # 丝印避开沉金开窗（留 1px 余量，防止印到金面上）
    silk = line & ~morph.grow(gold, 1.0)
    silk, clear = add_pupils(silk, gold, eyes)

    # 沉金外圈：一条 1.2mm 宽的金线，作为画面边框
    # 金环以内的线稿保留，金环以外清空（否则板边会留一圈碎线）
    ring = annulus(RING_IN, RING_OUT)
    silk &= radius_map() < (RING_IN - 0.18)
    gold = gold | ring

    return {
        "silk": silk & circ,            # 黑丝印（GTO）
        "gold": gold & circ,            # 沉金开窗（GTS）
        "clear": clear & circ,          # 高光：开窗层挖空 -> 露白阻焊
        "ring": ring & circ,
        "line": raw,
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


def main():
    m = build_masks()
    ppm = 1 / SCALE
    st = morph.stroke_width(m["silk"], ppm)
    print("丝印线宽 P5=%.3f P50=%.3f  <0.155mm=%.1f%%" %
          (st["p5"], st["p50"], 100 * st["frac_under"]))
    for k in ("silk", "gold", "clear"):
        print(f"  {k}: {int(m[k].sum())} px")
    preview(m, ppm=16, path=os.path.join(ROOT, "assets", "medallion_v6.png"))


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
    if "clear" in masks:
        img = Image.composite(Image.new("RGB", (W, H), MASK_C), img, blit(masks["clear"]))
    img = Image.composite(Image.new("RGB", (W, H), SILK), img, blit(masks["silk"]))

    hx, hy, hd = hole()
    r = hd / 2 * ppm
    ImageDraw.Draw(img).ellipse([cx + hx * ppm - r, cy - hy * ppm - r,
                                 cx + hx * ppm + r, cy - hy * ppm + r],
                                fill=(198, 190, 172))
    if path:
        img.save(path)
    return img


if __name__ == "__main__":
    main()
