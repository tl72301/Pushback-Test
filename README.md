# Pushback test

> Designed and directed by Thomas Liberman, with AI assistance for implementation, question drafting, screening, and analysis.

**How often does Claude change its answer when you push back?**

This repo measures how four Claude Opus versions (4.6, 4.8, 5 and 5.5) respond when a user disagrees with them on a judgment question that has no right answer:

1. The model picks between two options, for example two names for a coffee shop.
2. The user says the other option is better, either with no reason or with a short reason.
3. The model answers again, and code checks whether it changed its answer.

The main number is how often each model changes its answer when given **no reason**. The with-reason version is the control. A model that switches less without a reason, but still updates when given one, is resisting empty pushback rather than just being stubborn.

The plan, including the verdict rules and the automatic pilot checks, is in [PREREGISTRATION.md](PREREGISTRATION.md). It was committed publicly before any data was collected.

## Results

All four studies are finished. **[RESULTS.md](RESULTS.md)** brings them together: the preregistered verdicts, every model's rates on both question banks, and the limits.

- **Main study (confirmatory):** Opus 5.5 changed its answer after pushback with no reason 0.0% of the time, against 37.7% for Opus 4.6. Verdict: difference detected.
- **Replication on a new question bank (confirmatory):** 0.0% against 51.0%. Verdict: difference detected, so the main result replicates.
- **The control:** Opus 5.5 almost never changed its answer when given a reason either. So it keeps its first answer under any pushback, rather than resisting empty pushback in particular.

Each study's automatic report, with every answer, is in its `runs*/full/` folder. The design decisions, and what AI did, are under [Who did what](RESULTS.md#who-did-what).

## How it runs

One click on **Actions → Pushback test → Run workflow** runs the whole study on GitHub Actions through Anthropic's Message Batches API:

1. The pilot runs.
2. The preregistered checks are applied by code.
3. The full run starts automatically if the checks pass.
4. The report and chart are written, and every step is committed back to this repo.

When it finishes, or if it needs attention, the workflow opens an issue. Each run can wait up to about 5½ hours for a batch. After that it saves, stops and starts the next run for its study, which continues where it stopped, so slow batches don't need you to press anything.

## Follow-up: Sonnet and Fable

An exploratory follow-up runs the same test on Sonnet 4.6, Sonnet 5, Fable 5 and Fable 5.1, with the wording fixed at the main study's "standard". Its plan is in [PREREGISTRATION-FOLLOWUP.md](PREREGISTRATION-FOLLOWUP.md). **Run workflow** runs it by default (study `follow-up`); choose `main` for the original study. Its results go to `runs-followup/`, separate from the main study's.

## Replication on a new question bank

A replication repeats the main study's confirmatory test (Opus 5.5 vs Opus 4.6) on a new bank of 60 questions, screened by Astra in two rounds, and runs the same bank on Sonnet and Fable. Its plan is in [PREREGISTRATION-REPLICATION.md](PREREGISTRATION-REPLICATION.md). Run it with study `replication` (Opus and Sonnet) and study `replication-fable` (Fable). The two can run at the same time, and their results go to `runs-replication/` and `runs-replication-fable/`.

## Files

| File | What it is |
|---|---|
| `RESULTS.md` | The write-up of all four studies |
| `summarize.py`, `results.svg` | Rebuilds the write-up's numbers and chart from the saved results, with no API calls |
| `questions.json` | The judgment questions, reasons, and pushback wordings |
| `study.json` | Models, settings, and budgets |
| `study-followup.json` | The same for the Sonnet and Fable follow-up |
| `questions-replication.json` | The replication's question bank |
| `study-replication.json`, `study-replication-fable.json` | Settings for the replication, on Opus and Sonnet and on Fable |
| `PREREGISTRATION-REPLICATION.md` | The replication's plan |
| `reviews/` | Astra's screens of both question banks |
| `PREREGISTRATION-FOLLOWUP.md` | The follow-up's plan |
| `pushback.py` | Runs the study and writes reports |
| `tests/test_pipeline.py` | Offline end-to-end test against a simulated Batch API with planted change rates |
| `.github/workflows/pushback.yml` | The GitHub Actions workflow |
| `runs/` | Every answer, the reports, and the charts |
| `runs-followup/` | The same for the follow-up |
| `runs-replication/`, `runs-replication-fable/` | The same for the replication |

## Reproduce it

All four published studies are finished, and their `runs*/progress.json` files say so. Running one of them again, on GitHub or locally, only prints that it's finished. It never overwrites the results.

**Rebuild the published analyses.** No API key, no API calls, no cost.

- `python summarize.py` recomputes the numbers in RESULTS.md and rewrites `results.svg` from the saved answers.
- `python tests/test_pipeline.py` runs the offline tests, including a check that the saved results match the reports.
- `python pushback.py report` also works without a key, but it rewrites each study's `report.md` with the current code: new timestamps, plus sections added after the main study ran. Use it only if you want that.

**Resume an unfinished run.** Run the workflow again with the same study. It continues where it stopped, without resubmitting any batch it has already recorded.

**Start a new run.** A new run is a new experiment, with its own plan and its own results folder. Never delete the published `runs*` folders.

1. Copy a study file, such as `study.json`, to `study-NAME.json`. Give it a new `name`, and set `runs_dir` to a folder at the repo root that doesn't exist yet, such as `runs-NAME`.
2. Locally: set `ANTHROPIC_API_KEY`, then run `PUSHBACK_STUDY=study-NAME.json python pushback.py run`.
3. On GitHub Actions, in a fork with the `ANTHROPIC_API_KEY` secret: add `NAME` to the study options in `.github/workflows/pushback.yml`, then run the workflow with that study. It reads `study-NAME.json` and commits only its own folder.
