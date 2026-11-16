# -*- coding: utf-8 -*-
"""v13 = v12 严格等比缩小 0.5 cm（板宽 56 -> 51 mm），长宽比不变。

做法：对 RS-274X / Excellon 文本做纯坐标仿射变换（x,y -> k*x, k*y），
不重跑图像处理链路，因此所有图元、层叠、极性、相对位置逐点等比，
历史 v12 产物完全不动。
"""
import os
import re
import hashlib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "gerber12")
OUT = os.path.join(ROOT, "build", "gerber13")
ZIP = os.path.join(ROOT, "build", "Kisara_Pendant_6L_ENIG_v13.zip")

K = 51.0 / 56.0                      # 5.6 -> 5.1 cm
BASE = "kisara_medallion."
EXTS = ["GTL", "G2", "G3", "G4", "G5", "GBL",
        "GTS", "GBS", "GTO", "GBO", "GKO", "TXT"]

COORD = re.compile(r"([XY])(-?\d+)")
ADD_C = re.compile(r"(%ADD\d+C,)([0-9.]+)(\*%)")
DATA_LINE = re.compile(r"^[XY]-?\d+")
TOOL = re.compile(r"^(T\d+C)([0-9.]+)$")
DRILL_COORD = re.compile(r"([XY])(-?[0-9.]+)")


def scale_gerber(text):
    out = []
    for line in text.splitlines():
        if line.startswith("%ADD") and "C," in line:
            m = ADD_C.match(line)
            if m:                                     # 圆形孔径直径同步缩放
                line = f"{m.group(1)}{float(m.group(2)) * K:.4f}{m.group(3)}"
        elif DATA_LINE.match(line) and re.search(r"D0[123]\*", line):
            line = COORD.sub(
                lambda m: m.group(1) + str(int(round(int(m.group(2)) * K))),
                line)
        out.append(line)
    return "\n".join(out) + "\n"


def scale_drill(text):
    out = []
    for line in text.splitlines():
        m = TOOL.match(line)
        if m:                                         # 刀具直径
            line = f"{m.group(1)}{float(m.group(2)) * K:.3f}"
        elif re.match(r"^[XY]-?[0-9.]", line):        # 孔位坐标
            line = DRILL_COORD.sub(
                lambda m: m.group(1) + f"{float(m.group(2)) * K:.3f}",
                line)
        out.append(line)
    return "\n".join(out) + "\n"


def coords(path):
    """回读某个 Gerber 的所有坐标（mm）。"""
    pts = []
    with open(path, "r", encoding="ascii") as f:
        for line in f:
            if DATA_LINE.match(line) and re.search(r"D0[123]\*", line):
                d = {m.group(1): int(m.group(2)) / 1e6
                     for m in COORD.finditer(line)}
                if "X" in d or "Y" in d:
                    pts.append(d)
    return pts


def bbox(path):
    pts = coords(path)
    # 逐点补全省略的模态坐标
    xs, ys, cx, cy = [], [], 0.0, 0.0
    for p in pts:
        cx = p.get("X", cx)
        cy = p.get("Y", cy)
        xs.append(cx)
        ys.append(cy)
    return min(xs), min(ys), max(xs), max(ys)


def main():
    os.makedirs(OUT, exist_ok=True)
    for ext in EXTS:
        src = os.path.join(SRC, BASE + ext)
        dst = os.path.join(OUT, BASE + ext)
        with open(src, "r", encoding="ascii") as f:
            t = f.read()
        t = scale_drill(t) if ext == "TXT" else scale_gerber(t)
        with open(dst, "w", encoding="ascii", newline="\n") as f:
            f.write(t)

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ext in EXTS:
            z.write(os.path.join(OUT, BASE + ext), BASE + ext)

    print(f"K = {K:.9f}   (56 -> {56*K:.3f} mm ; 63.5 -> {63.5*K:.4f} mm)")
    print("\n--- 板框回读 ---")
    x0, y0, x1, y1 = bbox(os.path.join(OUT, BASE + "GKO"))
    print(f"GKO  X {x0:+.3f} .. {x1:+.3f}   Y {y0:+.3f} .. {y1:+.3f}")
    print(f"     宽 {x1-x0:.3f} mm  高 {y1-y0:.3f} mm  长宽比 {(x1-x0)/(y1-y0):.6f}")

    print("\n--- 各层包围盒（mm） ---")
    for ext in EXTS[:-2]:
        x0, y0, x1, y1 = bbox(os.path.join(OUT, BASE + ext))
        print(f"  {ext:4s}  X {x0:+8.3f}..{x1:+8.3f}   Y {y0:+8.3f}..{y1:+8.3f}")

    print("\n--- 钻孔 ---")
    with open(os.path.join(OUT, BASE + "TXT"), "r", encoding="ascii") as f:
        for line in f:
            if TOOL.match(line) or DRILL_COORD.search(line):
                print("  " + line.strip())

    print("\n--- 6 铜层 md5 ---")
    for ext in ["GTL", "G2", "G3", "G4", "G5", "GBL"]:
        with open(os.path.join(OUT, BASE + ext), "rb") as f:
            print(f"  {ext:4s} {hashlib.md5(f.read()).hexdigest()}")

    with zipfile.ZipFile(ZIP) as z:
        bad = z.testzip()
        print(f"\nzip  {os.path.basename(ZIP)}  {len(z.namelist())} files  "
              f"testzip={bad}")
    print("OUT", OUT)


if __name__ == "__main__":
    main()
