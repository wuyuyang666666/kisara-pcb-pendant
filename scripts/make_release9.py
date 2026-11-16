# -*- coding: utf-8 -*-
"""v9 生产文件：复用 v8 的写出逻辑，只替换设计模块与输出目录。

输出 build/gerber9/，保留 build/gerber3/ 里的 v8 原始 Gerber 不被覆盖。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_release8 as R
import design9 as D

R.D = D
R.OUT = os.path.join(D.ROOT, "build", "gerber9")

if __name__ == "__main__":
    R.main()
