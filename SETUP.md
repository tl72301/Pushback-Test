# Setup and reproduction

The published studies are complete, and this repository includes their saved responses and run state. You can rebuild the analysis without an API key. Collecting a new dataset requires a separate configuration and output directory.

## Rebuild the saved analysis

From a local checkout of the repository, run:

```bash
python summarize.py
python tests/test_pipeline.py
```

The first command prints the cross-study tables and writes `results.svg`. The second runs the offline tests. Neither command makes model API calls.

## Start a separate experiment

Fork or clone the repository and open a terminal at its root. Install the runner's dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a copy of the main study configuration with a new output directory. This command stops if either name is already in use:

```bash
python - <<'PY'
import json
from pathlib import Path
config, output = Path("study-local.json"), Path("runs-local")
if config.exists() or output.exists():
    raise SystemExit("Choose unused configuration and output names.")
study = json.loads(Path("study.json").read_text())
study["runs_dir"] = str(output)
config.write_text(json.dumps(study, indent=2) + "\n")
PY
```

For a different published study, copy its configuration instead of `study.json`. Review the selected models, question bank, settings, and budget before collection. Preview the configuration without submitting requests:

```bash
PUSHBACK_STUDY=study-local.json python pushback.py preview
```

Set `ANTHROPIC_API_KEY` in your local environment without committing it. This command submits paid requests and saves results to `runs-local/`:

```bash
PUSHBACK_STUDY=study-local.json python pushback.py run
```

## Resume or rerun

Resume with the same configuration and run command. For another independent experiment, use a new configuration and output directory. Preserve the published data and completed progress files. The existing GitHub Actions selections target the completed studies and do not start fresh experiments.

## Costs

The runner estimates costs from the selected configuration before submitting each batch. Check model availability and pricing before a new run. The original four studies cost $15.65 in total, including their pilots; that historical total is not a quote for future runs.
