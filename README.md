# Pushback test

**How often does Claude change its answer when you push back?**

This repo measures how four Claude Opus versions (4.6, 4.8, 5 and 5.5) respond when a user disagrees with them on a judgment question that has no right answer:

1. The model picks between two options, for example two names for a coffee shop.
2. The user says the other option is better, either with no reason or with a short reason.
3. The model answers again, and code checks whether it changed its answer.

The main number is how often each model changes its answer when given **no reason**. The with-reason version is the control. A model that switches less without a reason, but still updates when given one, is resisting empty pushback rather than just being stubborn.

The plan, including the verdict rules and the automatic pilot checks, is in [PREREGISTRATION.md](PREREGISTRATION.md). It was committed publicly before any data was collected.

## Results

These appear in `runs/full/report.md` and `runs/full/chart.svg` once the study finishes.

## How it runs

One click on **Actions → Pushback test → Run workflow** runs the whole study on GitHub Actions through Anthropic's Message Batches API:

1. The pilot runs.
2. The preregistered checks are applied by code.
3. The full run starts automatically if the checks pass.
4. The report and chart are written, and every step is committed back to this repo.

When it finishes, or if it needs attention, the workflow opens an issue.

## Follow-up: Sonnet and Fable

An exploratory follow-up runs the same test on Sonnet 4.6, Sonnet 5, Fable 5 and Fable 5.1, with the wording fixed at the main study's "standard". Its plan is in [PREREGISTRATION-FOLLOWUP.md](PREREGISTRATION-FOLLOWUP.md). **Run workflow** runs it by default (study `follow-up`); choose `main` for the original study. Its results go to `runs-followup/`, separate from the main study's.

## Files

| File | What it is |
|---|---|
| `questions.json` | The judgment questions, reasons, and pushback wordings |
| `study.json` | Models, settings, and budgets |
| `study-followup.json` | The same for the Sonnet and Fable follow-up |
| `PREREGISTRATION-FOLLOWUP.md` | The follow-up's plan |
| `pushback.py` | Runs the study and writes reports |
| `tests/test_pipeline.py` | Offline end-to-end test against a simulated Batch API with planted change rates |
| `.github/workflows/pushback.yml` | The GitHub Actions workflow |
| `runs/` | Every answer, the reports, and the charts |
| `runs-followup/` | The same for the follow-up |

## Reproduce it

1. Fork the repo.
2. Add an `ANTHROPIC_API_KEY` secret.
3. Run the workflow.

To test for free first, run `python tests/test_pipeline.py`. It needs no API key.
