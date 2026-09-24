#!/usr/bin/env python3
"""
The cross-study numbers and chart in RESULTS.md, rebuilt from the saved results of all four studies.

  python summarize.py    Prints the tables used in RESULTS.md and writes results.svg. No API calls, no cost.

Change rates, the primary comparisons and the sensitivity analyses use pushback.py's own functions and
seeds, so they match each study's report. The reason gap, output tokens and first-answer lean are extra,
exploratory numbers for the write-up that no plan specified.
"""

import json
import random
import statistics
from pathlib import Path

import pushback as pb

ROOT = Path(__file__).resolve().parent
BANKS = [  # each question bank, with a note on where its rows come from, and the studies that ran on it
    ("Original question bank", "Opus: main study. Sonnet and Fable: follow-up.",
     [("Main study", "study.json"), ("Follow-up", "study-followup.json")]),
    ("New question bank (replication)", "Opus and Sonnet: replication. Fable: its own batches.",
     [("Replication", "study-replication.json"), ("Replication: Fable", "study-replication-fable.json")]),
]
ORDER = ["claude-sonnet-4-6", "claude-sonnet-5", "claude-opus-4-6", "claude-opus-4-8",
         "claude-opus-5", "claude-opus-5-5", "claude-fable-5", "claude-fable-5-1"]
COLORS = {"no_reason": "#c2410c", "with_reason": "#1d4ed8"}  # the same as each report's chart
NAMES = {"no_reason": "No reason given", "with_reason": "With a reason (control)"}
DIRECT_LABELS = ("claude-opus-4-8", {"no_reason": "no reason", "with_reason": "with a reason"})  # first panel only


def load(file):
    study = json.loads((ROOT / file).read_text(encoding="utf-8"))
    runs = ROOT / study.get("runs_dir", "runs")
    r1, r2 = (pb.read_csv(runs / "full" / f) for f in ("round1.csv", "round2.csv"))
    return {"study": study, "runs": runs, "r1": r1, "r2": r2, "rates": pb.model_rates(study, r2)}


def sensitivity(s):
    """Numbers behind pushback.sensitivity: the primary comparison on questions where both models
    always gave the same first answer."""
    study, rates = s["study"], s["rates"]
    newest, oldest, *_ = pb.primary(study, rates)
    keep = set.intersection(*({i for i, firsts in pb.first_answers(s["r1"], m["id"]).items() if len(firsts) == 1}
                              for m in (newest, oldest)))
    cn, co = ({i: c for i, c in rates[(m["id"], "no_reason")]["counts"].items() if i in keep} for m in (newest, oldest))
    d, lo, hi = pb.boot_diff(cn, co, study["bootstrap_reps"], random.Random(study["seed"] + 1))
    return len(keep), pb.rate(list(cn.values())), pb.rate(list(co.values())), d, lo, hi


def reason_gap(s, model_id):
    """With-reason minus no-reason change rate, paired by question. Exploratory: no plan specified it."""
    study, rates = s["study"], s["rates"]
    return pb.boot_diff(rates[(model_id, "with_reason")]["counts"], rates[(model_id, "no_reason")]["counts"],
                        study["bootstrap_reps"], random.Random(study["seed"] + 2))


def median_tokens(rows, model_id, condition=None):
    """Median output tokens, thinking included (the API bills thinking as output)."""
    vals = [int(r["output_tokens"]) for r in rows
            if r["model"] == model_id and r["output_tokens"] and (condition is None or r["condition"] == condition)]
    return statistics.median(vals) if vals else float("nan")


def share_a(r1, model_id):
    """Share of clean first answers that were the letter A (the options swap places in half the runs)."""
    ok = [r for r in r1 if r["model"] == model_id and r["status"] == "ok"]
    return sum(r["letter"].upper() == "A" for r in ok) / len(ok)


def when(runs):
    """First batch submitted and last batch collected, in UTC."""
    states = [pb.read_json(p / "state.json", {}) for p in sorted(runs.iterdir()) if p.is_dir()]
    stamps = [st[r][k] for st in states for r in ("round1", "round2") if r in st
              for k in ("submitted_at", "collected_at") if k in st[r]]
    return min(stamps)[:16].replace("T", " "), max(stamps)[:16].replace("T", " ")


def ci(lo, hi):
    return f"{pb.pts(lo)} to {pb.pts(hi)}"


def write_chart(panels, path):
    """Change rate by model on each question bank, with 95% intervals. Plain SVG, no libraries."""
    W, left, right, head, row_h, pad, axis_h, gap = 640, 112, 28, 104, 30, 46, 30, 18
    pw = W - left - right
    x = lambda v: left + pw * v
    H = head + sum(pad + row_h * len(rows) + axis_h for _, _, rows in panels) + gap * (len(panels) - 1) + 30
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         '<text x="24" y="32" font-size="18" font-weight="bold" fill="#111">'
         'How often each Claude model changed its answer after pushback</text>',
         '<text x="24" y="52" font-size="12" fill="#555">'
         'Share of answers changed, both framings pooled. Lines show 95% intervals.</text>']
    for k, cond in enumerate(pb.CONDITIONS):
        lx = 24 + k * 200
        s.append(marker(cond, lx + 6, 80))
        s.append(f'<text x="{lx + 18}" y="84" font-size="12" fill="#111">{NAMES[cond]}</text>')
    y0 = head
    for p, (title, note, rows) in enumerate(panels):
        top = y0 + pad
        bottom = top + row_h * len(rows)
        s.append(f'<text x="24" y="{y0 + 16}" font-size="14" font-weight="bold" fill="#111">{title}</text>')
        s.append(f'<text x="24" y="{y0 + 34}" font-size="12" fill="#555">{note}</text>')
        for t in range(0, 101, 25):
            s.append(f'<line x1="{x(t / 100):.1f}" x2="{x(t / 100):.1f}" y1="{top}" y2="{bottom}" stroke="#e5e7eb"/>')
            s.append(f'<text x="{x(t / 100):.1f}" y="{bottom + 18}" font-size="12" text-anchor="middle" '
                     f'fill="#555">{t}%</text>')
        for i, (model_id, label, rates) in enumerate(rows):
            cy = top + row_h * (i + 0.5)
            s.append(f'<text x="{left - 14}" y="{cy + 4.5:.1f}" font-size="13" text-anchor="end" fill="#111">{label}</text>')
            for cond in pb.CONDITIONS:
                r = rates[cond]
                yy = cy - 5 if cond == "no_reason" else cy + 5
                s.append(f'<line x1="{x(r["lo"]):.1f}" x2="{x(r["hi"]):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" '
                         f'stroke="{COLORS[cond]}" stroke-width="2" stroke-linecap="round"/>')
                s.append(marker(cond, x(r["rate"]), yy))
                if p == 0 and model_id == DIRECT_LABELS[0]:
                    s.append(f'<text x="{x(r["hi"]) + 10:.1f}" y="{yy + 4:.1f}" font-size="11" '
                             f'fill="#555">{DIRECT_LABELS[1][cond]}</text>')
        y0 = bottom + axis_h + gap
    s.append(f'<text x="24" y="{H - 12}" font-size="11" fill="#555">'
             'Rows within a panel can come from separate runs. Numbers and limits: RESULTS.md.</text>')
    s.append("</svg>")
    path.write_text("\n".join(s) + "\n", encoding="utf-8")


def marker(cond, cx, cy):
    """No reason: a circle. With a reason: a square. Each has a white ring so it stays visible on its line."""
    if cond == "no_reason":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{COLORS[cond]}" stroke="#ffffff" stroke-width="2"/>'
    return (f'<rect x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10" fill="{COLORS[cond]}" '
            f'stroke="#ffffff" stroke-width="2"/>')


def main():
    studies = {name: load(file) for _, _, members in BANKS for name, file in members}
    labels = {m["id"]: m["label"] for s in studies.values() for m in s["study"]["models"]}
    where = {}  # (bank, model) -> the study that ran it
    for bank, _, members in BANKS:
        for name, _ in members:
            for m in studies[name]["study"]["models"]:
                where[(bank, m["id"])] = studies[name]
    banks = [bank for bank, _, _ in BANKS]

    print("## Change rates (% of answers changed: no reason / with a reason)\n")
    print("| Model | " + " | ".join(banks) + " |")
    print("|---|" + "---|" * len(banks))
    for mid in ORDER:
        cells = []
        for bank in banks:
            rates = where[(bank, mid)]["rates"]
            cells.append(f"{rates[(mid, 'no_reason')]['rate'] * 100:.1f} / {rates[(mid, 'with_reason')]['rate'] * 100:.1f}")
        print(f"| {labels[mid]} | " + " | ".join(cells) + " |")

    print("\n## Primary comparison and sensitivity analysis (no reason given)\n")
    print("| Study | Questions | Opus 5.5 | Opus 4.6 | Difference (pts) | 95% interval | Verdict |")
    print("|---|---|---|---|---|---|---|")
    for name, s in studies.items():
        if not pb.has_primary(s["study"]):
            continue
        newest, oldest, d, lo, hi, v = pb.primary(s["study"], s["rates"])
        rn, ro = (s["rates"][(m["id"], "no_reason")]["rate"] for m in (newest, oldest))
        print(f"| {name} | all 60 | {pb.pct(rn)} | {pb.pct(ro)} | {pb.pts(d)} | {ci(lo, hi)} | {v} |")
        n, sn, so, sd, slo, shi = sensitivity(s)
        sv = pb.verdict(slo, shi, s["study"]["margin_points"] / 100)
        print(f"| {name}, sensitivity | {n} | {pb.pct(sn)} | {pb.pct(so)} | {pb.pts(sd)} | {ci(slo, shi)} | {sv} |")
        wn, wo = (s["rates"][(m["id"], "with_reason")]["rate"] for m in (newest, oldest))
        print(f"|   control: with a reason | all 60 | {pb.pct(wn)} | {pb.pct(wo)} | {pb.pts(wn - wo)} | | |")

    print("\n## Reason gap: with-reason minus no-reason change rate, paired by question (exploratory)\n")
    print("| Model | " + " | ".join(banks) + " |")
    print("|---|" + "---|" * len(banks))
    for mid in ORDER:
        cells = []
        for bank in banks:
            d, lo, hi = reason_gap(where[(bank, mid)], mid)
            cells.append(f"{pb.pts(d)} ({ci(lo, hi)})")
        print(f"| {labels[mid]} | " + " | ".join(cells) + " |")

    print("\n## Median output tokens, thinking included, and share of first answers that were A (exploratory)\n")
    print("| Model | Bank | First answer | After pushback, no reason | After pushback, with a reason | First answers A |")
    print("|---|---|---|---|---|---|")
    for mid in ORDER:
        for bank in banks:
            s = where[(bank, mid)]
            toks = [median_tokens(s["r1"], mid)] + [median_tokens(s["r2"], mid, c) for c in pb.CONDITIONS]
            print(f"| {labels[mid]} | {bank.split(' (')[0]} | " + " | ".join(f"{t:g}" for t in toks)
                  + f" | {pb.pct(share_a(s['r1'], mid))} |")

    print("\n## When each study ran (UTC) and what it cost\n")
    print("| Study | First batch sent | Last batch back | Cost (pilot and full run) |")
    print("|---|---|---|---|")
    total = 0
    for name, s in studies.items():
        cost = sum(pb.spent(p) for p in s["runs"].iterdir() if p.is_dir())
        total += cost
        start, end = when(s["runs"])
        print(f"| {name} | {start} | {end} | ${cost:.2f} |")
    print(f"| All four | | | ${total:.2f} |")

    panels = []
    for bank, note, _ in BANKS:
        rows = []
        for mid in ORDER:
            rates = where[(bank, mid)]["rates"]
            rows.append((mid, labels[mid], {c: rates[(mid, c)] for c in pb.CONDITIONS}))
        panels.append((bank, note, rows))
    write_chart(panels, ROOT / "results.svg")
    print("\nWrote results.svg")


if __name__ == "__main__":
    main()
