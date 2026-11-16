"""从最终 6 层 v14 生成 4 层沉金版：外观层逐字节照搬，内层铜换成两个真实图形。

嘉立创 FR-4 只有 1/2/4/6 层，不做 3 层（官方 q1i50492）。
4 层版用「2~4 层沉金 EDA 专用券」，无晒单义务（t7i37587 / 37595）。
丝印、阻焊开窗、板框、钻孔完全不变，因此成品图案效果与 6 层版一致。
"""
import os
import shutil
import hashlib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "gerber14")
DST = os.path.join(ROOT, "build", "gerber4L")
ZIP = os.path.join(ROOT, "build", "Kisara_Pendant_4L_ENIG.zip")
BASE = "kisara_medallion."

# 输出层 <- v14 源层；外观层一对一原样复制
MAP = {
    "GTL": ("GTL", True),    # 顶层铜
    "G1":  ("G2", False),    # 内层1 铜，复用真实图形（不是空白假层）
    "G2":  ("G3", False),    # 内层2 铜，复用真实图形
    "GBL": ("GBL", True),    # 底层铜
    "GTS": ("GTS", True),    # 顶层阻焊开窗 = 沉金区
    "GBS": ("GBS", True),
    "GTO": ("GTO", True),    # 顶层白丝印
    "GBO": ("GBO", True),
    "GKO": ("GKO", True),    # 板框
    "TXT": ("TXT", True),    # 钻孔：唯一 NPTH 挂孔
}


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def build():
    os.makedirs(DST, exist_ok=True)
    for out, (src, _exact) in MAP.items():
        s = os.path.join(SRC, BASE + src)
        d = os.path.join(DST, BASE + out)
        shutil.copyfile(s, d)

    files = [BASE + k for k in MAP]
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(DST, name), arcname=name)

    return files


def verify(files):
    print("== 外观层字节一致性（4L vs v14）==")
    for out, (src, exact) in MAP.items():
        a = os.path.join(DST, BASE + out)
        b = os.path.join(SRC, BASE + src)
        same = md5(a) == md5(b)
        print("  %-4s <- %-4s  %s" % (out, src, "一致" if same else "已改"))
        if exact and not same:
            raise SystemExit("外观层 %s 被改动，图案效果会变" % out)

    print("\n== 内层铜非空白 ==")
    for layer in ("G1", "G2"):
        p = os.path.join(DST, BASE + layer)
        txt = open(p, "r", encoding="ascii", errors="ignore").read()
        draws = txt.count("D02") + txt.count("D01")
        print("  %s 绘图指令 %d 条，文件 %d 字节" % (layer, draws, os.path.getsize(p)))
        if draws < 10:
            raise SystemExit("内层 %s 疑似空白" % layer)

    print("\n== 钻孔 ==")
    txt = open(os.path.join(DST, BASE + "TXT"), encoding="ascii").read()
    print("  " + " / ".join(txt.splitlines()[4:6]))

    z = zipfile.ZipFile(ZIP)
    print("\n== 打包 ==")
    print("  %s  %d 文件  testzip=%s  %d 字节" %
          (os.path.basename(ZIP), len(z.namelist()), z.testzip(), os.path.getsize(ZIP)))
    print("  文件: " + ", ".join(n.split(".")[-1] for n in z.namelist()))


if __name__ == "__main__":
    verify(build())
