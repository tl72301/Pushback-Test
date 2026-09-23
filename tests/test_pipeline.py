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


def run_study(mode):
    work = Path(tempfile.mkdtemp())
    for f in ("pushback.py", "study.json", "questions.json"):
        shutil.copy(REPO / f, work / f)
    return work, run_in(work, mode)


def run_in(work, mode):
    env = dict(os.environ, PYTHONPATH=str(FAKE), ANTHROPIC_API_KEY="fake", PUSHBACK_POLL_SECONDS="0",
               FAKE_MODE=mode, GITHUB_ACTIONS="false")
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


if __name__ == "__main__":
    test_normal()
    test_floor()
    test_prose()
    test_technical_failures()
    test_recheck_finished_pilot()
    print("All tests passed.")
