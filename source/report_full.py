"""Build runs/<label>/report.md (+ report.json) from status.json and each task's grades.json.

Groups (per task)
  A    A_direct
  B    B_1
  Bx4  the attempt Bx4_select chose among B_1..B_4; credits = B_1..B_4 + the selector
  C    C_final; credits = B_1 (reference run) + propose + both probes + compose + final
end-to-end time assumes the runs that could overlap did (Bx4: slowest B + selector;
C: B_1 + propose + slower probe + compose + final); "sum" adds every call.
Reference only (no group): B_1..B_4 spread, Bx4 by best provided-test rate, best of B_1..B_4
by hidden score (uses hidden data, so it is an upper bound, never a group result).
"""
import argparse
import statistics
from pathlib import Path

from common import RUNS_DIR, read_json, write_json

B = ["B_1", "B_2", "B_3", "B_4"]
C_PARTS = ["B_1", "C_propose", "C_probe_general", "C_probe_specific", "C_compose", "C_final"]


def fmt(x, nd=1):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    label = ap.parse_args().label
    root = RUNS_DIR / label
    st = read_json(root / "status.json")
    jobs = st["jobs"]
    out = {"label": label, "model": st.get("model"), "tasks": {}}
    lines = [f"# Full run {label}: model {st.get('model')}, effort {st.get('effort') or 'not set'}", "",
             f"Credits recorded: {st.get('credits_total')} (of which outside any job: "
             f"{st.get('credits_overhead', 0)}). Stopped for budget: {st.get('stopped_for_budget')}. "
             f"Error: {bool(st.get('error'))}.", ""]
    summary = ["## Summary (score per task; credits in brackets)", "",
               "| task | A | B | Bx4 | C |", "|---|---|---|---|---|"]

    for t in st["tasks"]:
        gpath = root / t / "grades.json"
        gj = read_json(gpath) if gpath.exists() else {"grades": {}, "metric": {}}
        g = gj["grades"]
        J = lambda n: jobs.get(f"{t}/{n}", {})  # noqa: E731
        cred = lambda *ns: round(sum(J(n).get("credits") or 0 for n in ns), 3)  # noqa: E731
        wall = lambda n: J(n).get("wall_s") or 0  # noqa: E731
        sc = lambda n: (g.get(n) or {}).get("score")  # noqa: E731
        sel = (J("Bx4_select").get("out") or {})
        choice = sel.get("choice")
        groups = {
            "A": {"run": "A_direct", "score": sc("A_direct"), "credits": cred("A_direct"),
                  "e2e_s": wall("A_direct"), "sum_s": wall("A_direct")},
            "B": {"run": "B_1", "score": sc("B_1"), "credits": cred("B_1"),
                  "e2e_s": wall("B_1"), "sum_s": wall("B_1")},
            "Bx4": {"run": choice, "score": sc(choice) if choice else None,
                    "credits": cred(*B, "Bx4_select"),
                    "e2e_s": max(wall(b) for b in B) + wall("Bx4_select"),
                    "sum_s": sum(wall(b) for b in B) + wall("Bx4_select"), "chosen_by": sel.get("by")},
            "C": {"run": "C_final", "score": sc("C_final"), "credits": cred(*C_PARTS),
                  "e2e_s": wall("B_1") + wall("C_propose") + max(wall("C_probe_general"), wall("C_probe_specific"))
                  + wall("C_compose") + wall("C_final"),
                  "sum_s": sum(wall(n) for n in C_PARTS)},
        }
        bs = [sc(b) for b in B if sc(b) is not None]
        ref = {"B_runs": {b: sc(b) for b in B},
               "B_spread": {"min": min(bs), "median": statistics.median(bs), "max": max(bs)} if bs else None,
               "Bx4_by_best_provided": {"run": sel.get("best_visible"),
                                        "score": sc(sel["best_visible"]) if sel.get("best_visible") else None},
               "best_of_B_by_hidden_upper_bound": max(bs) if bs else None,
               "C_probes": {n: sc(n) for n in ("C_probe_general", "C_probe_specific")}}
        notes = []
        for k, j in sorted(jobs.items()):
            if not k.startswith(t + "/"):
                continue
            n = k.split("/", 1)[1]
            if j.get("state") in ("failed", "skipped"):
                notes.append(f"{n}: {j.get('state')} ({j.get('failure', '')}) {str(j.get('error', ''))[:160]}")
            if j.get("timed_out"):
                notes.append(f"{n}: hit the time limit" + (" (credits not reported by kiro-cli)"
                                                            if not j.get("credits") else ""))
            if j.get("infra_retries"):
                notes.append(f"{n}: {j['infra_retries']} infrastructure re-run(s)")
        for n, gg in g.items():
            if gg.get("note"):
                notes.append(f"{n}: {gg['note']}")
        out["tasks"][t] = {"metric": gj.get("metric"), "groups": groups, "reference": ref, "notes": notes}

        m = gj.get("metric") or {}
        lines += [f"## {t}", "", f"Score: {m.get('score', '?')}. Secondary: {m.get('secondary', '-')}.", "",
                  "| group | deliverable | score | secondary | credits | end-to-end min | sum of calls min |",
                  "|---|---|---|---|---|---|---|"]
        for name, gr in groups.items():
            sec = (g.get(gr["run"]) or {}).get("secondary") if gr["run"] else None
            lines.append(f"| {name} | {gr['run'] or '-'} | {fmt(gr['score'])} | {fmt(sec)} | "
                         f"{fmt(gr['credits'], 2)} | {fmt(gr['e2e_s'] / 60)} | {fmt(gr['sum_s'] / 60)} |")
        lines += ["", f"Reference: B_1..B_4 scores {[fmt(sc(b)) for b in B]}"
                      + (f" (min {fmt(ref['B_spread']['min'])}, median {fmt(ref['B_spread']['median'])}, "
                         f"max {fmt(ref['B_spread']['max'])})" if ref["B_spread"] else "")
                  + f"; Bx4 chosen by {sel.get('by', '-')}; pick by best provided-test rate would be "
                    f"{ref['Bx4_by_best_provided']['run'] or '-'} ({fmt(ref['Bx4_by_best_provided']['score'])}); "
                    f"C probes {', '.join(f'{k} {fmt(v)}' for k, v in ref['C_probes'].items())}.", ""]
        if notes:
            lines += ["Notes:", ""] + [f"- {x}" for x in notes] + [""]
        summary.append(f"| {t} | " + " | ".join(f"{fmt(groups[k]['score'])} ({fmt(groups[k]['credits'], 1)})"
                                                for k in ("A", "B", "Bx4", "C")) + " |")

    text = "\n".join(lines[:4] + summary + [""] + lines[4:]) + "\n"
    (root / "report.md").write_text(text, encoding="utf-8")
    write_json(root / "report.json", out)
    print(text)
    # pre-registered verdicts (PREREGISTRATION_full1.md); a failure here must not lose the report
    import subprocess
    import sys
    j = subprocess.run([sys.executable, str(Path(__file__).with_name("judge_full.py")), "--label", label],
                       capture_output=True, text=True)
    if j.returncode:
        print("judge_full.py failed:", j.stderr[-2000:], file=sys.stderr)


if __name__ == "__main__":
    main()
