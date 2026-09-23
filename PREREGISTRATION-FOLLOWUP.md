# Preregistration: Pushback test follow-up (Sonnet and Fable)

Committed on 2026-09-23, before any follow-up data was collected. The Git history is the record. Any later change gets its own commit with a reason.

This follow-up was planned after the main study's results were known ([PREREGISTRATION.md](PREREGISTRATION.md), [runs/full/report.md](runs/full/report.md)). In the main study, Opus 5 and Opus 5.5 almost never changed their answer, with or without a reason. The follow-up asks whether other current Claude models show the same pattern. **Everything here is exploratory.** Nothing in it changes or re-tests the main study's confirmatory result.

## Question

How often do Sonnet 4.6, Sonnet 5, Fable 5 and Fable 5.1 change their answer to a judgment question when the user pushes back, with no reason and with a reason?

## Design

The same as the main study (see Design in PREREGISTRATION.md), except:

- **Models.** claude-sonnet-4-6 and claude-sonnet-5 with adaptive thinking at low effort. claude-fable-5 and claude-fable-5-1 always think; low effort. Settings are in `study-followup.json`. No Opus models are run again.
- **Unchanged.** The same 60 questions, the same 12 pilot questions, framings, repeats, scoring and maximum output tokens. No system prompt, default temperature, Message Batches API.
- **Wording.** Pushback wording is fixed at "standard", the wording the main study used, so the results can be compared with it.
- **Results.** Saved in `runs-followup/`, separate from the main study's `runs/`.

## Pilot rules (applied automatically by code)

The main study's rules as amended on 2026-09-23 (see Deviations in PREREGISTRATION.md), with rule 2 reported but not acted on:

1. At least 95% technically successful requests for every model. Otherwise, stop.
2. The pooled no-reason change rate is reported, but the wording is not switched if it falls outside 5% to 95%. After the main study, some of these models may sit near 0%. Switching wording would break comparability with the main study, and a floor is itself a result.
3. The pooled with-reason rate must be at least the no-reason rate. Otherwise, stop and review.
4. The projected full-run cost must be within the $60 budget. Otherwise, stop.

## Analyses (all exploratory)

- Each model's no-reason and with-reason change rates, both framings pooled, with 95% intervals from resampling questions (2,000 bootstrap resamples, fixed seed).
- Within-family comparisons of the no-reason rate, using the main study's verdict rule: Sonnet 5 minus Sonnet 4.6, and Fable 5.1 minus Fable 5.
- The same control reading as the main study: a lower no-reason rate is read as resisting empty pushback only when the with-reason rate doesn't drop by as much.
- The evaluation label effect per model, and each model's rate of answering in prose.
- Comparisons with the main study's Opus results are made in the write-up, not the automatic report, and are described as comparisons between separate runs.

## Reporting commitments

- All results are published with the raw data and code, including null results and floors.
- No result here is described as confirmatory.

## Known limits

- The limits listed in PREREGISTRATION.md apply here too.
- This follow-up was designed after seeing the main study's results.
- Comparisons with the Opus models are between separate runs made on different occasions.
