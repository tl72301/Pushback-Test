# Pushback test

**How often does Claude change its answer when a user disagrees?**

> Designed and directed by Thomas Liberman, with AI assistance for implementation, question drafting, screening, and analysis.

This project tests how eight Claude models respond to disagreement on two banks of judgment questions. Across four studies, each model chose between two options, then answered again after the user favored the other option, either without a reason or with a short reason.

1. The model chooses A or B.
2. The user argues for the other option, with or without a reason.
3. Code records whether the model changes its choice.

The main measure is the rate of switching after disagreement without a reason. The with-reason condition tests whether adding a reason changes that rate. Because the questions have no single correct answer, switching is not automatically a mistake, and keeping an answer is not automatically better.

I shaped the research strategy, reviewed and revised the question banks, and made the final design decisions. The [plans](PREREGISTRATION.md), [screening records](reviews/), and [contribution statement](RESULTS.md#who-did-what) document those choices and the AI assistance used to carry them out.

## Results

All four studies are complete. [RESULTS.md](RESULTS.md) contains the findings, the preregistered verdicts, and the limits of the experiment.

- **Main study, confirmatory:** Opus 5.5 switched after disagreement without a reason in 0 of 480 eligible responses (0.0%), compared with 37.7% for Opus 4.6. The preregistered verdict was "difference detected."
- **Replication, confirmatory:** On a second question bank, the rates were again 0 of 480 (0.0%) for Opus 5.5 and 51.0% for Opus 4.6. This met the preregistered replication criterion.
- **With a reason:** Opus 5.5 also rarely switched in this condition: 1.2% in the main study and 0.4% in the replication. Its lower switching rate was not specific to disagreement without a reason. The study does not establish that keeping its answer was the better response.

The reports and saved responses are in each study's `runs*/full/` folder. The two primary comparisons are confirmatory. All other comparisons and the supplementary analyses are exploratory.

## How it runs

The completed studies ran on GitHub Actions through Anthropic's Message Batches API. For a configured study that has not finished, the workflow runs the pilot, applies the preregistered checks, starts the full run if the checks pass, and saves the responses and reports.

This repository includes the completed run state. Starting the existing workflow again resumes an unfinished run or reports that the selected study is already complete. Forking the repository does not reset that state. To collect new data, follow the separate-run instructions in [SETUP.md](SETUP.md).

When it finishes, or if it needs attention, the workflow opens an issue. Each run can wait up to about 5½ hours for a batch. After that it saves, stops and starts the next run for its study, which continues where it stopped, so slow batches don't need you to press anything.

## Follow-up: Sonnet and Fable

The exploratory follow-up tested Sonnet 4.6, Sonnet 5, Fable 5 and Fable 5.1 on the original bank, using the main study's standard pushback wording. Its plan is in [PREREGISTRATION-FOLLOWUP.md](PREREGISTRATION-FOLLOWUP.md) and its results are in [runs-followup/](runs-followup/). The workflow's `follow-up` selection refers to this completed study.

## Replication on a new question bank

The replication repeated the primary comparison, Opus 5.5 versus Opus 4.6, on a new bank of 60 questions. The bank was screened by Astra in two rounds and reviewed by me. Opus and Sonnet results are in [runs-replication/](runs-replication/); Fable results are in [runs-replication-fable/](runs-replication-fable/). [PREREGISTRATION-REPLICATION.md](PREREGISTRATION-REPLICATION.md) records the plan. The workflow's `replication` and `replication-fable` selections refer to these completed studies.

## Files

| File | What it is |
|---|---|
| `RESULTS.md` | The write-up of all four studies |
| `SETUP.md` | Rebuilding the analysis, and starting a separate experiment |
| `summarize.py`, `results.svg` | Recomputes the cross-study tables and chart from saved responses; does not rewrite RESULTS.md |
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

## Reproduce the analysis

Run these commands from the repository root to rebuild the cross-study numbers and chart and check the offline pipeline. Neither command needs an API key or makes model API calls.

```bash
python summarize.py
python tests/test_pipeline.py
```

To collect a new dataset, follow [SETUP.md](SETUP.md). Use a separate configuration and output directory so the published responses and completed run state remain intact. New collection requires API access and incurs usage charges.
