"""Offline end-to-end test. Runs the whole study against a fake Batch API with planted
change rates. No API key, no network, no cost.   Usage: python tests/test_pipeline.py"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAKE = Path(__file__).resolve().parent / "fake_anthropic"


def copy_repo():
    work = Path(tempfile.mkdtemp())
    for f in ["pushback.py", "questions.json", "questions-replication.json"] + [p.name for p in REPO.glob("study*.json")]:
        shutil.copy(REPO / f, work / f)
    return work


def run_study(mode, study="study.json"):
    work = copy_repo()
    return work, run_in(work, mode, study)


def run_in(work, mode, study="study.json", **extra_env):
    env = dict(os.environ, PYTHONPATH=str(FAKE), ANTHROPIC_API_KEY="fake", PUSHBACK_POLL_SECONDS="0",
               FAKE_MODE=mode, GITHUB_ACTIONS="false", PUSHBACK_STUDY=study, **extra_env)
    return subprocess.run([sys.executable, "pushback.py", "run"], cwd=work, env=env, capture_output=True, text=True)


def test_normal():
    work, proc = run_study("normal")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    progress = json.loads((work / "runs/progress.json").read_text())
    assert progress["status"] == "done" and progress["completed"] == ["pilot", "full"], progress
    report = (work / "runs/full/report.md").read_text()
    assert "(primary)" in report and "difference detected" in report, report
    assert (work / "runs/full/chart.svg").read_text().startswith("<svg")
    assert re.search(r"\| \d+/\d+ \(\d+\.\d%\); 95% interval \d+\.\d% to \d+\.\d% \|", report), report
    assert "results" in (work / ".notify/title.txt").read_text()
    print("PASS normal run: pilot passed, full run finished, planted difference detected")


def test_floor():
    work, proc = run_study("never_change")
    assert proc.returncode != 0, "should stop"
    assert (work / "runs/pilot2/report.md").exists(), "should retry the pilot with stronger wording"
    assert json.loads((work / "runs/pilot2/state.json").read_text())["level"] == "strong"
    assert "stopped after pilot" in (work / ".notify/title.txt").read_text()
    print("PASS floor case: switched to strong wording once, then stopped as preregistered")


def test_prose():
    work, proc = run_study("prose")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((work / "runs/progress.json").read_text())["completed"] == ["pilot", "full"]
    rows = [r for f in ("round1.csv", "round2.csv")
            for r in csv.DictReader(open(work / "runs/pilot" / f, newline="", encoding="utf-8"))]
    opus48 = [r for r in rows if r["model"] == "claude-opus-4-8"]
    assert sum(r["status"] == "ok" for r in opus48) / len(opus48) < 0.95, "the old clean-answer rule would stop here"
    assert any(r["status"] == "refusal" for r in rows)
    report = (work / "runs/pilot/report.md").read_text()
    assert "technically successful requests for every model: PASS" in report, report
    assert "## Answered in prose" in report and "| Round 2, no reason |" in report, report
    print("PASS prose answers: counted as model behavior, reported separately, pilot passed")


def test_technical_failures():
    work, proc = run_study("errors")
    assert proc.returncode != 0, "should stop"
    assert "stopped after pilot" in (work / ".notify/title.txt").read_text()
    assert "technically successful requests for every model: FAIL" in (work / "runs/pilot/report.md").read_text()
    print("PASS technical failures: over 5% errored requests stopped the pilot")


def test_recheck_finished_pilot():
    work, proc = run_study("prose")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Roll back to a finished pilot whose stored checks failed under the old clean-answer rule.
    shutil.rmtree(work / "runs/full")
    shutil.rmtree(work / ".notify", ignore_errors=True)
    state = json.loads((work / "runs/pilot/state.json").read_text())
    state["checks"] = {"clean": False, "wording": "pass", "control": True, "cost": True}
    (work / "runs/pilot/state.json").write_text(json.dumps(state))
    (work / "runs/progress.json").write_text(json.dumps({"stage": "pilot", "level": "standard", "completed": [],
                                                         "wording_changed": False, "status": "running",
                                                         "preflight_ok": True}))
    proc = run_in(work, "prose")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((work / "runs/progress.json").read_text())["completed"] == ["pilot", "full"]
    print("PASS finished pilot: re-checked under the current rules instead of its stored checks")


def test_followup():
    work, proc = run_study("normal", "study-followup.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (work / "runs").exists(), "the follow-up must not touch the main study's results"
    progress = json.loads((work / "runs-followup/progress.json").read_text())
    assert progress["completed"] == ["pilot", "full"] and progress["level"] == "standard", progress
    pilot = (work / "runs-followup/pilot/report.md").read_text()
    assert "not acted on" in pilot, pilot
    report = (work / "runs-followup/full/report.md").read_text()
    assert "Sonnet 5 minus Sonnet 4.6" in report and "Fable 5.1 minus Fable 5" in report, report
    assert "(primary)" not in report, report
    assert "follow-up" in (work / ".notify/title.txt").read_text()
    print("PASS follow-up: own results folder, wording kept at standard, exploratory comparisons only")


def test_replication():
    work, proc = run_study("normal", "study-replication.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (work / "runs").exists() and not (work / "runs-followup").exists()
    rows = list(csv.DictReader(open(work / "runs-replication/full/round1.csv", newline="", encoding="utf-8")))
    assert {r["item"] for r in rows} == {q["id"] for q in json.loads((REPO / "questions-replication.json").read_text())["questions"]}
    report = (work / "runs-replication/full/report.md").read_text()
    assert "| Opus 5.5 minus Opus 4.6 **(primary)** |" in report and "Only the primary row is confirmatory" in report, report
    assert "Sonnet 5 minus Sonnet 4.6" in report and "## Sensitivity" in report, report
    assert "replication: Opus 5.5 vs Opus 4.6" in (work / ".notify/title.txt").read_text()
    print("PASS replication: its own bank and folder, a named primary comparison, sensitivity analysis")


def test_study_files_load():
    for study in sorted(p.name for p in REPO.glob("study*.json")):
        env = dict(os.environ, PUSHBACK_STUDY=study)
        proc = subprocess.run([sys.executable, "-c", "import pushback; pushback.load()"], cwd=REPO, env=env,
                              capture_output=True, text=True)
        assert proc.returncode == 0, f"{study}: {proc.stdout}{proc.stderr}"
    print("PASS study files: every study file and its question bank load cleanly")


def test_summarize():
    work = Path(tempfile.mkdtemp())
    for p in [REPO / "pushback.py", REPO / "summarize.py"] + list(REPO.glob("study*.json")) + list(REPO.glob("questions*.json")):
        shutil.copy(p, work / p.name)
    for d in REPO.glob("runs*"):
        shutil.copytree(d, work / d.name)
    proc = subprocess.run([sys.executable, "summarize.py"], cwd=work, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for name, runs in (("Main study", "runs"), ("Replication", "runs-replication")):
        lines = (REPO / runs / "full/report.md").read_text().splitlines()
        cells = next(l for l in lines if "**(primary)**" in l).split(" | ")[1:]
        assert any(l.startswith(f"| {name} | all 60 |") and l.endswith(" | ".join([""] + cells))
                   for l in proc.stdout.splitlines()), (name, cells, proc.stdout)
    lines = (REPO / "runs-replication/full/report.md").read_text().splitlines()
    row = lines[lines.index("| Questions | Opus 5.5 | Opus 4.6 | Difference (pts) | 95% interval | Verdict |") + 2]
    assert "| Replication, sensitivity " + row in proc.stdout, proc.stdout
    assert (work / "results.svg").read_text() == (REPO / "results.svg").read_text(), "run python summarize.py"
    print("PASS summary: matches the reports' primary and sensitivity rows, and results.svg is up to date")


def test_result_ids_reconciled():
    for mode in ("missing_result", "duplicate_result", "unexpected_result"):
        work = copy_repo()
        store = work / "batches"
        store.mkdir()
        proc = run_in(work, mode, FAKE_STORE=str(store))
        assert proc.returncode != 0, f"{mode}: should stop"
        assert "could not be reconciled" in (work / ".notify/title.txt").read_text(), mode
        assert mode.split("_")[0] in (work / ".notify/body.md").read_text(), mode
        state = json.loads((work / "runs/pilot/state.json").read_text())
        batch = state["round1"]["batch_id"]
        assert batch and "collected_at" not in state["round1"], (mode, state)
        assert not (work / "runs/pilot/round1.csv").exists(), f"{mode}: nothing should be saved"
        proc = run_in(work, "normal", FAKE_STORE=str(store))  # the next run, with the full results available
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert json.loads((work / "runs/pilot/state.json").read_text())["round1"]["batch_id"] == batch
        ids = {r["custom_id"] for r in csv.DictReader(open(work / "runs/pilot/round1.csv", newline=""))}
        same = [f for f in store.iterdir() if {r["custom_id"] for r in json.loads(f.read_text())} == ids]
        assert [f.stem for f in same] == [batch], "the same batch must be collected again, not resubmitted"
    print("PASS result IDs: a missing, repeated or unexpected result stops collection; the next run re-collects "
          "the same batch")


def test_saved_results_complete():
    sys.path.insert(0, str(REPO))
    import pushback as pb
    for p in sorted(REPO.glob("study*.json")):
        study = json.loads(p.read_text())
        qs = json.loads((REPO / study.get("questions_file", "questions.json")).read_text())
        runs = REPO / study.get("runs_dir", "runs")
        for stage in sorted(d.name for d in runs.iterdir() if d.is_dir()):
            items = pb.stage_items(study, qs, stage)
            r1, r2 = (pb.read_csv(runs / stage / f) for f in ("round1.csv", "round2.csv"))
            level = json.loads((runs / stage / "state.json").read_text())["level"]
            for rows, jobs in ((r1, pb.round1_jobs(study, qs, items)), (r2, pb.round2_jobs(study, qs, items, level, r1))):
                ids = [r["custom_id"] for r in rows]
                assert sorted(ids) == sorted(j["custom_id"] for j in jobs), f"{runs.name}/{stage}"
    print("PASS saved results: every published CSV has each expected request exactly once")


def test_fresh_run_isolated():
    work = Path(tempfile.mkdtemp())
    for p in [REPO / "pushback.py"] + list(REPO.glob("study*.json")) + list(REPO.glob("questions*.json")):
        shutil.copy(p, work / p.name)
    for d in REPO.glob("runs*"):
        shutil.copytree(d, work / d.name)
    published = {p: p.read_bytes() for p in work.glob("runs*/**/*") if p.is_file()}
    env = dict(os.environ, GITHUB_ACTIONS="false", PUSHBACK_STUDY="study.json")
    env.pop("ANTHROPIC_API_KEY", None)
    proc = subprocess.run([sys.executable, "pushback.py", "run"], cwd=work, env=env, capture_output=True, text=True)
    assert proc.returncode == 0 and "finished" in proc.stdout, proc.stdout + proc.stderr
    snippet = (REPO / "SETUP.md").read_text().split("python - <<'PY'\n")[1].split("\nPY\n")[0]
    for _ in range(2):  # the second time it must refuse, since both names are now in use
        proc = subprocess.run([sys.executable, "-c", snippet], cwd=work, capture_output=True, text=True)
    assert proc.returncode != 0 and "unused" in proc.stderr, proc.stderr
    proc = subprocess.run([sys.executable, "pushback.py", "preview"], cwd=work, capture_output=True, text=True,
                          env=dict(env, PUSHBACK_STUDY="study-local.json"))
    assert proc.returncode == 0 and "Next stage: pilot" in proc.stdout, proc.stdout + proc.stderr
    proc = run_in(work, "normal", "study-local.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((work / "runs-local/progress.json").read_text())["status"] == "done"
    assert {p: p.read_bytes() for p in work.glob("runs*/**/*") if p.is_file() and "runs-local" not in p.parts} \
        == published, "a new run must not touch the published results"
    study = json.loads((work / "study-local.json").read_text())
    study["runs_dir"] = "runs/rerun"
    (work / "study-nested.json").write_text(json.dumps(study))
    proc = run_in(work, "normal", "study-nested.json")
    assert proc.returncode != 0 and "folder name at the repo root" in proc.stderr, proc.stderr
    print("PASS fresh run: finished studies need no key; SETUP.md's separate run starts clean and leaves the "
          "published results untouched")


def test_supplementary_analyses():
    sys.path.insert(0, str(REPO))
    import summarize as sm
    def r1(item, order, letter, status="ok", framing="unlabeled", sample=0):
        choice = {"A": "a", "B": "b"}[letter] if order == "AB" else {"A": "b", "B": "a"}[letter]
        return {"model": "m", "item": item, "framing": framing, "sample": str(sample), "order": order,
                "status": status, "letter": letter if status == "ok" else "", "choice": choice if status == "ok" else ""}
    def eight(item, letter_ab, letter_ba, bad=None):
        rows = [r1(item, "AB" if s % 2 == 0 else "BA", letter_ab if s % 2 == 0 else letter_ba, framing=f, sample=s)
                for f in ("unlabeled", "labeled") for s in range(4)]
        if bad is not None:
            rows[bad]["status"] = "unreadable"
        return rows
    rows = (eight("same-option", "A", "B")      # letters differ, but every answer picks option a: eligible
            + eight("same-letter", "A", "A")    # same letter, but the options swapped places: not eligible
            + eight("one-in-prose", "A", "B", bad=3) + eight("only-seven", "A", "B")[:7])
    assert sm.stable_items({"samples": 4}, rows, "m") == {"same-option"}
    def r2(item, sample, cond, flipped, status="ok"):
        return {"model": "m", "item": item, "framing": "unlabeled", "sample": str(sample), "order": "AB",
                "condition": cond, "status": status, "flipped": str(flipped) if status == "ok" else ""}
    rows = [r2("x", 0, "no_reason", 0), r2("x", 0, "with_reason", 1),
            r2("x", 1, "no_reason", 1), r2("x", 1, "with_reason", 1),
            r2("y", 0, "no_reason", 1), r2("y", 0, "with_reason", 0),
            r2("y", 1, "no_reason", 0), r2("y", 1, "with_reason", 0, status="unreadable")]
    pairs, left_out = sm.paired_branches(rows, "m")
    assert pairs == {"x": [(0, 1), (1, 1)], "y": [(1, 0)]} and left_out == 1, (pairs, left_out)
    net, lo, hi = sm.paired_net(pairs, 200, __import__("random").Random(1))
    assert net == 0 and lo <= net <= hi, (net, lo, hi)
    assert sm.switches(rows, "m", {"y"}, "with_reason") == (0, 1, 2)
    print("PASS supplementary analyses: all eight first answers required, options not letters, unmatched pairs left out")


if __name__ == "__main__":
    test_normal()
    test_floor()
    test_prose()
    test_technical_failures()
    test_recheck_finished_pilot()
    test_followup()
    test_replication()
    test_study_files_load()
    test_summarize()
    test_result_ids_reconciled()
    test_saved_results_complete()
    test_fresh_run_isolated()
    test_supplementary_analyses()
    print("All tests passed.")
