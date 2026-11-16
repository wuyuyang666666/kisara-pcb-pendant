#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出板框：DXF (R2000 / LWPOLYLINE 闭合) + SVG
坐标单位为 mm，原点左下角。
DXF 设置 $INSUNITS=4（毫米），嘉立创 EDA / AutoCAD 导入后比例即为 1:1。
"""

import os


def to_dxf(polylines, path, layer="BOARD_OUTLINE"):
    """polylines: [ ['pts': [(x,y)...], 'closed': bool, 'layer': str], ... ]"""
    out = []
    A = out.append
    A("0"); A("SECTION"); A("2"); A("HEADER")
    A("9"); A("$ACADVER"); A("1"); A("AC1015")
    A("9"); A("$INSUNITS"); A("70"); A("4")
    A("9"); A("$MEASUREMENT"); A("70"); A("1")
    A("0"); A("ENDSEC")

    A("0"); A("SECTION"); A("2"); A("TABLES")
    A("0"); A("TABLE"); A("2"); A("LAYER"); A("70"); A("1")
    for lay in sorted(set(p.get("layer", layer) for p in polylines) | {layer}):
        A("0"); A("LAYER"); A("2"); A(lay); A("70"); A("0")
        A("62"); A("7"); A("6"); A("CONTINUOUS")
    A("0"); A("ENDTAB")
    A("0"); A("ENDSEC")

    A("0"); A("SECTION"); A("2"); A("ENTITIES")
    for p in polylines:
        pts = p["pts"]
        closed = 1 if p.get("closed", True) else 0
        A("0"); A("LWPOLYLINE")
        A("8"); A(p.get("layer", layer))
        A("90"); A(str(len(pts)))
        A("70"); A(str(closed))
        A("43"); A("0.0")
        for x, y in pts:
            A("10"); A(f"{x:.4f}")
            A("20"); A(f"{y:.4f}")
    A("0"); A("ENDSEC")
    A("0"); A("EOF")

    with open(path, "w", encoding="ascii", newline="\r\n") as f:
        f.write("\n".join(out))


def to_svg(polylines, size_mm, path, title="", colors=None):
    w, h = size_mm
    colors = colors or {}
    body = []
    for p in polylines:
        pts = p["pts"]
        d = "M " + " L ".join(f"{x:.3f},{h - y:.3f}" for x, y in pts) + " Z"
        lay = p.get("layer", "")
        fill = p.get("fill", colors.get(lay, "none"))
        stroke = p.get("stroke", "#000000")
        sw = p.get("stroke_width", 0.15)
        body.append(
            f'  <path d="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" id="{p.get("id", "")}"/>'
        )
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm"
     viewBox="0 0 {w} {h}">
  <title>{title}</title>
{chr(10).join(body)}
</svg>
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
