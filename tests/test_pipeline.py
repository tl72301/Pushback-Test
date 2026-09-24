"""Offline end-to-end test. Runs the whole study against a fake Batch API with planted
change rates. No API key, no network, no cost.   Usage: python tests/test_pipeline.py"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAKE = Path(__file__).resolve().parent / "fake_anthropic"


def run_study(mode, study="study.json"):
    work = Path(tempfile.mkdtemp())
    for f in ["pushback.py", "questions.json", "questions-replication.json"] + [p.name for p in REPO.glob("study*.json")]:
        shutil.copy(REPO / f, work / f)
    return work, run_in(work, mode, study)


def run_in(work, mode, study="study.json"):
    env = dict(os.environ, PYTHONPATH=str(FAKE), ANTHROPIC_API_KEY="fake", PUSHBACK_POLL_SECONDS="0",
               FAKE_MODE=mode, GITHUB_ACTIONS="false", PUSHBACK_STUDY=study)
    return subprocess.run([sys.executable, "pushback.py", "run"], cwd=work, env=env, capture_output=True, text=True)


def test_normal():
    work, proc = run_study("normal")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    progress = json.loads((work / "runs/progress.json").read_text())
    assert progress["status"] == "done" and progress["completed"] == ["pilot", "full"], progress
    report = (work / "runs/full/report.md").read_text()
    assert "(primary)" in report and "difference detected" in report, report
    assert (work / "runs/full/chart.svg").read_text().startswith("<svg")
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
    print("All tests passed.")
