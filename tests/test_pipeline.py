"""Offline end-to-end test. Runs the whole study against a fake Batch API with planted
change rates. No API key, no network, no cost.   Usage: python tests/test_pipeline.py"""
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
    env = dict(os.environ, PYTHONPATH=str(FAKE), ANTHROPIC_API_KEY="fake", PUSHBACK_POLL_SECONDS="0",
               FAKE_MODE=mode, GITHUB_ACTIONS="false")
    proc = subprocess.run([sys.executable, "pushback.py", "run"], cwd=work, env=env, capture_output=True, text=True)
    return work, proc


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


if __name__ == "__main__":
    test_normal()
    test_floor()
    print("All tests passed.")
