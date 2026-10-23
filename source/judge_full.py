"""Apply the pre-registered decision rules (PREREGISTRATION_full1.md) to a finished full run.

usage: judge_full.py --label full1     reads runs/<label>/report.json (from report_full.py)
writes runs/<label>/judgement.md and judgement.json. No model call, no judgement by hand:
every verdict below comes from the rules in this file, fixed before any full-run score existed.
"""
import argparse

from common import RUNS_DIR, read_json, write_json

BINARY = {"humaneval", "swe1", "swe2"}  # score is 0 or 100
CONTINUOUS = {"commonmark", "jsonschema"}  # score is a pass rate in %
MIN_GAP = 3.0  # percentage points: a continuous difference must exceed max(B range, MIN_GAP)
CEILING = 99.0


def cont_cmp(x, y, sx, sy, thr):
    if sx is None or sy is None:
        return "无数据"
    d = sx - sy
    if d > thr:
        return f"{x} 优于 {y}（差 {d:+.1f}，阈值 {thr:.1f}）"
    if d < -thr:
        return f"{y} 优于 {x}（差 {d:+.1f}，阈值 {thr:.1f}）"
    return f"差异未超过阈值（差 {d:+.1f}，阈值 {thr:.1f}）"


def bin_cmp(x, sx, p, n):
    """x (one 0/100 outcome) against the B family (n runs, success share p)."""
    if sx is None or n == 0:
        return "无数据"
    if p == 0 and sx == 100:
        return f"{x} 优于 B 系（{x} 成功，B 的 {n} 次全部失败；单次观察）"
    if p == 1 and sx == 0:
        return f"B 系优于 {x}（{x} 失败，B 的 {n} 次全部成功；单次观察）"
    return f"无法区分（{x}={sx:.0f}，B 成功 {round(p * n)}/{n}）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    label = ap.parse_args().label
    rep = read_json(RUNS_DIR / label / "report.json")
    out, lines = {}, [f"# 判定结果：{label}（按 PREREGISTRATION_full1.md 的规则自动计算）", ""]
    tally = {"Q1": {}, "Q2": {}, "Q3": {}}
    for t, r in rep["tasks"].items():
        g = r["groups"]
        s = {k: g[k]["score"] for k in ("A", "B", "Bx4", "C")}
        c = {k: g[k]["credits"] for k in ("A", "B", "Bx4", "C")}
        bs = [v for v in r["reference"]["B_runs"].values() if v is not None]
        res = {"scores": s, "credits": c, "B_runs": bs}
        if t in CONTINUOUS:
            rng = (max(bs) - min(bs)) if len(bs) >= 2 else None
            thr = max(rng if rng is not None else 0.0, MIN_GAP)
            res.update(noise=f"B 四次极差 {rng:.1f}" if rng is not None else "B 不足 2 次，噪声未知",
                       threshold=thr)
            a_b = cont_cmp("A", "B", s["A"], s["B"], thr)
            bx_b = cont_cmp("Bx4", "B", s["Bx4"], s["B"], thr)
            c_bx = cont_cmp("C", "Bx4", s["C"], s["Bx4"], thr)
            c_b = cont_cmp("C", "B", s["C"], s["B"], thr)
            ceiling = all(v is not None and v >= CEILING for v in s.values()) and \
                all(v >= CEILING for v in bs)
        else:
            n = len(bs)
            p = (sum(v == 100 for v in bs) / n) if n else 0.0
            res.update(noise=f"B 成功 {sum(v == 100 for v in bs)}/{n}", threshold=None)
            a_b = bin_cmp("A", s["A"], p, n)
            bx_b = ("无法区分（Bx4 是 B 四次之一）" if p in (0, 1) else
                    f"描述：Bx4 {'选中了成功的一次' if s['Bx4'] == 100 else '选中了失败的一次'}（B 成功 {round(p * n)}/{n}）")
            c_bx = bin_cmp("C", s["C"], p, n)
            c_b = c_bx
            ceiling = n > 0 and p == 1 and s["A"] == 100 and s["C"] == 100
        cheaper_a = c["A"] is not None and c["B"] is not None and c["A"] < c["B"]
        if t in CONTINUOUS:
            not_worse = a_b.startswith("A 优于") or a_b.startswith("差异未超过")
            worse = a_b.startswith("B 优于")
        else:  # binary: A's single outcome against B's 4 runs
            n_ok, n_b = sum(v == 100 for v in bs), len(bs)
            not_worse = s["A"] == 100 and n_b > 0 and n_ok in (0, n_b)
            worse = s["A"] == 0 and n_b > 0 and n_ok == n_b
            if s["A"] == 0 and n_b > 0 and n_ok == 0:
                not_worse = False  # everyone failed: nothing to say about A
        if not_worse and cheaper_a:
            q1 = "直接调用即可（不差于 B 且更便宜）"
        elif not_worse:
            q1 = "A 不差于 B，但不更便宜"
        elif worse:
            q1 = "需要 harness（B 优于 A）"
        else:
            q1 = "无法判断"
        q2 = ("选择有用（Bx4 优于 B）" if bx_b.startswith("Bx4 优于") else
              "选择反而更差" if bx_b.startswith("B 优于") else "未检出选择的作用")
        if c_bx.startswith("C 优于"):
            q3 = "改提示词本身有效（C 优于等预算的 Bx4）"
        elif c_bx.startswith("Bx4 优于") or c_bx.startswith("B 系优于"):
            q3 = "C 不如多跑几次（Bx4 优于 C）"
        elif t in CONTINUOUS and c_b.startswith("C 优于"):
            q3 = "C 优于 B，但可用多跑几次解释（不优于 Bx4）"
        else:
            q3 = "未检出差异"
        if ceiling:
            q1 = q2 = q3 = "到顶：所有组都满分，只比成本"
        elif t in BINARY:  # one 0/100 outcome per group: a decisive verdict is still weak
            q1 = q1 + "（单次观察）" if q1.startswith(("直接", "需要", "A 不差")) else q1
            q3 = q3 + "（单次观察）" if q3.startswith(("改提示词", "C 不如")) else q3
        res.update(compare={"A_vs_B": a_b, "Bx4_vs_B": bx_b, "C_vs_Bx4": c_bx, "C_vs_B": c_b},
                   Q1=q1, Q2=q2, Q3=q3, ceiling=ceiling,
                   cost_ratio_vs_B={k: (round(c[k] / c["B"], 2) if c["B"] else None) for k in ("A", "Bx4", "C")})
        for q in ("Q1", "Q2", "Q3"):
            tally[q][res[q]] = tally[q].get(res[q], 0) + 1
        out[t] = res
        lines += [f"## {t}", "",
                  f"- 分数：A {s['A']}，B {s['B']}，Bx4 {s['Bx4']}，C {s['C']}；B 四次 {bs}；{res['noise']}",
                  f"- 成本（相对 B 的倍数）：{res['cost_ratio_vs_B']}",
                  f"- A vs B：{a_b}", f"- Bx4 vs B：{bx_b}", f"- C vs Bx4（主比较）：{c_bx}",
                  f"- C vs B：{c_b}",
                  f"- Q1 直接调用够不够：{q1}", f"- Q2 多跑几次再挑有没有用：{q2}", f"- Q3 自动改提示词有没有用：{q3}", ""]
    lines += ["## 跨题汇总（只计数，不平均）", ""]
    for q, d in tally.items():
        lines.append(f"- {q}：" + "；".join(f"{k} × {v}" for k, v in d.items()))
    (RUNS_DIR / label / "judgement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(RUNS_DIR / label / "judgement.json", {"label": label, "tasks": out, "tally": tally})
    print("\n".join(lines))


if __name__ == "__main__":
    main()
