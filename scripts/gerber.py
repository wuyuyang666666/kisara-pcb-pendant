#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerber RS-274X 生成器（简单多边形版）
坐标系：mm，格式 %FSLAX46Y46*%，1mm = 1000000 单位
只支持：区域填充（G36/G37）、折线（D01/D02）、圆形孔径线
"""

import math

SCALE = 1000000


def _c(v):
    return f"{int(round(v * SCALE))}"


class Gerber:
    def __init__(self, name, polarity_dark=True):
        self.lines = [
            f"G04 {name}*",
            "%TF.GenerationSoftware,WorkBuddy,KisaraPendant,1.0*%",
            "%TF.SameCoordinates,Original*%",
            "%FSLAX46Y46*%",
            "%MOMM*%",
            "%LPD*%",
        ]
        self.apertures = {}
        self.cur = None

    def aperture(self, d, shape="C", params=(0.1,)):
        """注册孔径，返回 D 码编号"""
        if d in self.apertures:
            return d
        self.apertures[d] = (shape, params)
        p = "X".join(f"{x:.4f}" for x in params)
        self.lines.append(f"%ADD{d}{shape},{p}*%")
        return d

    def select(self, d):
        if self.cur != d:
            self.lines.append(f"D{d}*")
            self.cur = d

    def fill(self, polys):
        """区域填充，polys 可含多个环（同一区域内的孔需按奇偶）"""
        self.lines.append("G36*")
        for pts in polys:
            if len(pts) < 3:
                continue
            x0, y0 = pts[0]
            self.lines.append(f"X{_c(x0)}Y{_c(y0)}D02*")
            for x, y in pts[1:]:
                self.lines.append(f"X{_c(x)}Y{_c(y)}D01*")
            self.lines.append(f"X{_c(x0)}Y{_c(y0)}D01*")
        self.lines.append("G37*")

    def polyline(self, pts, d, closed=False):
        self.select(d)
        P = list(pts)
        if closed and P[0] != P[-1]:
            P.append(P[0])
        if len(P) < 2:
            return
        x0, y0 = P[0]
        self.lines.append(f"X{_c(x0)}Y{_c(y0)}D02*")
        for x, y in P[1:]:
            self.lines.append(f"X{_c(x)}Y{_c(y)}D01*")

    def circle(self, cx, cy, r, d):
        """用折线逼近圆（孔径线画圆不方便，直接区域填充）"""
        pts = [(cx + r * math.cos(2 * math.pi * i / 48),
                cy + r * math.sin(2 * math.pi * i / 48)) for i in range(48)]
        self.fill([pts])

    def save(self, path):
        with open(path, "w", encoding="ascii", newline="\n") as f:
            f.write("\n".join(self.lines + ["M02*"]))


def excellon(holes, path, header_tool_d=0.5):
    """
    holes: [(x, y, d), ...]  mm
    输出 Excellon 钻孔文件（公制，坐标 mm）
    """
    tools = sorted(set(round(h[2], 3) for h in holes))
    out = ["M48", ";EXCELLON", "FMAT,2", "METRIC,TZ"]
    for i, d in enumerate(tools, start=1):
        out.append(f"T{i}C{d:.3f}")
    out.append("%")
    out.append("G90")
    out.append("G05")
    for i, d in enumerate(tools, start=1):
        out.append(f"T{i}")
        for x, y, dd in holes:
            if round(dd, 3) != d:
                continue
            out.append(f"X{x:.3f}Y{y:.3f}")
    out.append("T0")
    out.append("M30")
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(out))
