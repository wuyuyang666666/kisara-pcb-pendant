#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L1 图案层几何（mm 坐标，原点左下，y 向上）
数组顺序 = 绘制顺序（后者压前者）

配色分工（对成品观感至关重要）：
  silk 白丝印 —— 高对比细节：眼白、眉、嘴、发丝线
  black 阻焊  —— 眼内暗部（在黑底上仅用作眼白上的瞳仁）
  gold 沉金  —— 小面积点缀：高光、角、蝴蝶结、裙线、领线

工艺：沉金最小 0.15mm，丝印最小 0.15mm；此处一律 >= 0.28mm。
"""

import math

LW = 0.42
LW_THIN = 0.30

CX = 27.65
FY = 83.4          # 脸中心 y
EY = FY + 0.9      # 眼高


def ell(cx, cy, rx, ry, n=48, rot=0.0):
    a = math.radians(rot)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(a) - y * math.sin(a),
                    cy + x * math.sin(a) + y * math.cos(a)))
    return out


def stroke(pts, w=LW):
    P = list(pts)
    if len(P) < 2:
        return []
    left, right = [], []
    n = len(P)
    for i in range(n):
        if i == 0:
            dx, dy = P[1][0] - P[0][0], P[1][1] - P[0][1]
        elif i == n - 1:
            dx, dy = P[-1][0] - P[-2][0], P[-1][1] - P[-2][1]
        else:
            dx = P[i + 1][0] - P[i - 1][0]
            dy = P[i + 1][1] - P[i - 1][1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        left.append((P[i][0] + nx, P[i][1] + ny))
        right.append((P[i][0] - nx, P[i][1] - ny))
    return left + list(reversed(right))


def almond(cx, cy, w, h, tilt=0.0):
    """杏仁形（上缘拱、下缘浅）"""
    pts = []
    N = 26
    for i in range(N):
        t = math.pi * i / (N - 1)
        pts.append((cx - w / 2 + w * i / (N - 1), cy + h / 2 * math.sin(t) ** 0.8))
    for i in range(N):
        t = math.pi * i / (N - 1)
        pts.append((cx + w / 2 - w * i / (N - 1), cy - h / 2.5 * math.sin(t) ** 0.85))
    a = math.radians(tilt)
    out = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * math.cos(a) - dy * math.sin(a),
                    cy + dx * math.sin(a) + dy * math.cos(a)))
    return out


def build(cx=CX):
    L = []

    # ============ 1. 眼白（白丝印） ============
    for sgn in (-1, 1):
        ex = cx + sgn * 3.0
        L.append({"pts": almond(ex, EY, 3.0, 3.4, tilt=sgn * 4), "kind": "gold",
                  "id": f"eyewhite_{sgn}"})

    # ============ 3. 瞳（黑） + 高光（白） ============
    hl = []
    for sgn in (-1, 1):
        ex = cx + sgn * 3.0
        L.append({"pts": ell(ex + sgn * 0.06, EY - 0.15, 1.12, 1.34, 30), "kind": "black",
                  "id": f"pupil_{sgn}"})
        hl.append({"pts": ell(ex + sgn * 0.52, EY + 0.55, 0.46, 0.50, 20), "kind": "silk",
                   "id": f"hl_{sgn}"})

    # ============ 4. 眉（白） ============
    for sgn in (-1, 1):
        ex = cx + sgn * 3.0
        L.append({"pts": stroke([(ex - 1.15, EY + 2.55), (ex - 0.1, EY + 2.85),
                                 (ex + 1.05, EY + 2.45)], 0.30), "kind": "gold",
                  "id": f"brow_{sgn}"})

    # ============ 5. 嘴（白） ============
    L.append({"pts": stroke([(cx - 0.75, FY - 4.9), (cx, FY - 5.3),
                             (cx + 0.75, FY - 4.9)], 0.34), "kind": "gold", "id": "mouth"})

    # ============ 6. 刘海分界线（金，弧） ============
    bang = []
    for i in range(19):
        t = i / 18.0
        x = cx - 5.3 + 10.6 * t
        y = 89.4 - 2.1 * math.sin(math.pi * t) ** 0.75
        bang.append((x, y))
    L.append({"pts": stroke(bang, 0.46), "kind": "gold", "id": "bangs"})

    # ============ 8. 水手服领（金） ============
    for sgn in (-1, 1):
        L.append({"pts": stroke([(cx, 68.4), (cx + sgn * 5.0, 72.4),
                                 (cx + sgn * 6.4, 71.4)], LW),
                  "kind": "gold", "id": f"collar_{sgn}"})

    # ============ 9. 蝴蝶结（金） ============
    L.append({"pts": [(cx, 68.6), (cx - 2.4, 70.3), (cx - 3.1, 68.0),
                      (cx - 2.1, 66.4), (cx, 67.9)], "kind": "gold", "id": "bow_L"})
    L.append({"pts": [(cx, 68.6), (cx + 2.4, 70.3), (cx + 3.1, 68.0),
                      (cx + 2.1, 66.4), (cx, 67.9)], "kind": "gold", "id": "bow_R"})
    L.append({"pts": ell(cx, 68.3, 0.72, 0.72, 24), "kind": "gold", "id": "bow_knot"})

    # ============ 10. 裙摆线（金） ============
    for i, (yy, half) in enumerate([(50.4, 9.4), (47.4, 11.2)]):
        L.append({"pts": stroke([(cx - half, yy), (cx, yy + 0.55), (cx + half, yy)],
                                LW_THIN), "kind": "gold", "id": f"skirt_{i}"})

    # ============ 11. 腰线（金） ============
    L.append({"pts": stroke([(cx - 7.2, 55.3), (cx, 55.9), (cx + 7.2, 55.3)],
                            LW_THIN), "kind": "gold", "id": "waist"})

    # ============ 12. 眼中高光（最后画，压在一切之上） ============
    L.extend(hl)

    return L


if __name__ == "__main__":
    it = build()
    print("items", len(it))
    for k in ("silk", "gold", "black"):
        print(k, sum(1 for i in it if i["kind"] == k))
