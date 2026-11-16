#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包交付：Gerber ZIP + 清单"""
import os, sys, zipfile, hashlib, json

ROOT = r"D:\计算机\资料\WorkBuddy\2026-11-05-22-23-13"
GB = os.path.join(ROOT, "build", "gerber")
OUT = os.path.join(ROOT, "build")

LAYER_DESC = {
    "kisara.GKO": "板框外形（0.10mm 线，闭合）",
    "kisara.GTL": "L1 顶层铜（整板铺铜）",
    "kisara.G2":  "L2 内层1 地平面",
    "kisara.G3":  "L3 内层2 隐藏图案（负极性挖空）",
    "kisara.G4":  "L4 内层3 电源平面",
    "kisara.G5":  "L5 内层4 地平面",
    "kisara.GBL": "L6 底层铜（整板铺铜）",
    "kisara.GTS": "L1 阻焊开窗（= 沉金图案）",
    "kisara.GBS": "L6 阻焊开窗（= 背面金色心形）",
    "kisara.GTO": "L1 丝印（眼中高光）",
    "kisara.TXT": "钻孔（Φ3.0 NPTH 挂孔）",
}


def main():
    zpath = os.path.join(OUT, "Kisara_Pendant_6L_Gerber.zip")
    files = sorted(os.listdir(GB))
    rows = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            p = os.path.join(GB, f)
            z.write(p, f)
            rows.append({
                "file": f,
                "desc": LAYER_DESC.get(f, ""),
                "bytes": os.path.getsize(p),
                "md5": hashlib.md5(open(p, "rb").read()).hexdigest()[:12],
            })

    manifest = {
        "project": "Kisara PCB pendant (Engage Kiss)",
        "board": json.load(open(os.path.join(OUT, "kisara_outline.json"), encoding="utf-8")),
        "files": rows,
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"ZIP: {zpath}  ({os.path.getsize(zpath)} B, {len(files)} files)")
    for r in rows:
        print(f"  {r['file']:12s} {r['bytes']:>7d}B  {r['desc']}")


if __name__ == "__main__":
    main()
