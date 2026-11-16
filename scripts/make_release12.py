# -*- coding: utf-8 -*-
"""v12 生产文件：复用 make_release11 的完整链路，只把设计模块换成 design12、
输出目录换成 build/gerber12/。6 铜层差异化图案、挖空极性全部沿用 v11。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design12 as D
import make_release11 as R

R.D = D
R.ROOT = D.ROOT
R.OUT = os.path.join(D.ROOT, "build", "gerber12")
R.SCALE, R.SRC = D.SCALE, D.SRC


def main():
    return R.main()


if __name__ == "__main__":
    main()
