#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerber 自检：语法完整性、坐标范围、区域闭合、层一致性、钻孔文件合法性
"""
import json
import os
import re
import sys

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
GB = os.path.join(ROOT, "build", "gerber")
JS = os.path.join(ROOT, "build", "kisara_outline.json")

SCALE = 1e6


def parse(fn):
    raw = open(fn, encoding="ascii", errors="replace").read()
    # 剔除 %...% 扩展命令与 G04 注释，避免把 FSLAX46 里的 46 当成坐标
    txt = "\n".join(l for l in raw.splitlines()
                     if not l.startswith("%") and not l.startswith("G04"))
    xs = [int(m) / SCALE for m in re.findall(r"X(-?\d+)", txt)]
    ys = [int(m) / SCALE for m in re.findall(r"Y(-?\d+)", txt)]
    return {
        "has_eof": "M02*" in raw,
        "has_fmt": "%FSLAX46Y46*%" in raw,
        "has_mm": "%MOMM*%" in raw,
        "g36": txt.count("G36*"),
        "g37": txt.count("G37*"),
        "n_coord": len(xs),
        "xmin": min(xs) if xs else None, "xmax": max(xs) if xs else None,
        "ymin": min(ys) if ys else None, "ymax": max(ys) if ys else None,
        "dark": txt.count("%LPD*%"), "clear": txt.count("%LPC*%"),
    }


def main():
    d = json.load(open(JS, encoding="utf-8"))
    W, H = d["size_mm"]
    print(f"板框 {W:.2f} x {H:.2f} mm   挂孔 {d['mount_hole']}")
    print(f"{'file':14s} {'coord':>7s} {'G36':>4s} {'G37':>4s} "
          f"{'x range':>17s} {'y range':>17s}  eof fmt mm")
    print("-" * 92)

    problems = []
    for fn in sorted(os.listdir(GB)):
        if not fn.lower().endswith((".gtl", ".gbl", ".gko", ".gts", ".gbs",
                                    ".gto", ".gbo", ".g1", ".g2", ".g3", ".g4", ".g5")):
            continue
        p = parse(os.path.join(GB, fn))
        xr = f"{p['xmin']:.2f}~{p['xmax']:.2f}" if p["xmin"] is not None else "-"
        yr = f"{p['ymin']:.2f}~{p['ymax']:.2f}" if p["ymin"] is not None else "-"
        print(f"{fn:14s} {p['n_coord']:>7d} {p['g36']:>4d} {p['g37']:>4d} "
              f"{xr:>17s} {yr:>17s}  "
              f"{'Y' if p['has_eof'] else 'N'}   {'Y' if p['has_fmt'] else 'N'}  "
              f"{'Y' if p['has_mm'] else 'N'}")

        if not p["has_eof"]:
            problems.append(f"{fn}: 缺少 M02 结束符")
        if not (p["has_fmt"] and p["has_mm"]):
            problems.append(f"{fn}: 缺少坐标格式或单位声明")
        if p["g36"] != p["g37"]:
            problems.append(f"{fn}: G36/G37 不配对 ({p['g36']}/{p['g37']})")
        if p["n_coord"]:
            if p["xmin"] < -0.01 or p["xmax"] > W + 0.01:
                problems.append(f"{fn}: X 超界 {p['xmin']:.2f}~{p['xmax']:.2f} (板宽 {W:.2f})")
            if p["ymin"] < -0.01 or p["ymax"] > H + 0.01:
                problems.append(f"{fn}: Y 超界 {p['ymin']:.2f}~{p['ymax']:.2f} (板高 {H:.2f})")

    # 板框闭合检查
    gko = open(os.path.join(GB, "kisara.GKO"), encoding="ascii").read()
    coords = re.findall(r"X(-?\d+)Y(-?\d+)D0([12])\*", gko)
    if coords:
        first = coords[0]
        last = coords[-1]
        if first[:2] != last[:2]:
            problems.append("GKO: 首尾坐标不一致，板框未闭合")

    # 钻孔
    txt = open(os.path.join(GB, "kisara.TXT"), encoding="ascii").read()
    if "M30" not in txt:
        problems.append("TXT: 缺少 M30")
    if "METRIC" not in txt:
        problems.append("TXT: 未声明公制")

    print("\n" + ("=" * 92))
    if problems:
        print(f"发现 {len(problems)} 个问题：")
        for q in problems:
            print("  ✗", q)
    else:
        print("✓ 全部检查通过")


if __name__ == "__main__":
    main()
