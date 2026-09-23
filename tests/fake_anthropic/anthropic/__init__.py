"""A fake Anthropic SDK for offline tests. It imitates the Batch API and plants known
change rates per model, so the test can check the pipeline recovers them."""
import hashlib
import os
import random
import re

__version__ = "fake"
_rng = random.Random(5)
_BATCHES = {}
_MODE = os.environ.get("FAKE_MODE", "normal")
_CHANGE = {"claude-opus-4-6": .55, "claude-opus-4-8": .45, "claude-opus-5": .35, "claude-opus-5-5": .15}


class NotFoundError(Exception):
    pass


class _O:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _answer(params):
    msgs, model = params["messages"], params["model"]
    last = msgs[-1]["content"]
    if _rng.random() < 0.01:
        return "I'd go with the first one."
    if len(msgs) == 1:
        a, b = re.search(r"A\) (.*)\nB\) (.*)\n", last).groups()
        pref = "A" if hashlib.md5(a.encode()).hexdigest() < hashlib.md5(b.encode()).hexdigest() else "B"
        other = "B" if pref == "A" else "A"
        return (pref if _rng.random() < .85 else other) + _rng.choice(["", "."])
    pushed = re.search(r"(?:think|toward) ([AB]) \(", last).group(1)
    previous = msgs[1]["content"].strip(" .")
    p = 0.0 if _MODE == "never_change" else _CHANGE[model] + (0.25 if "because" in last else 0)
    return pushed if _rng.random() < p else previous


class _Batches:
    def create(self, requests):
        batch_id = f"msgbatch_fake_{len(_BATCHES)}"
        _BATCHES[batch_id] = {"requests": requests, "polls": 0}
        return _O(id=batch_id)

    def retrieve(self, batch_id):
        b = _BATCHES[batch_id]
        b["polls"] += 1
        return _O(processing_status="ended" if b["polls"] > 1 else "in_progress",
                  request_counts=_O(processing=len(b["requests"]), succeeded=0, errored=0))

    def results(self, batch_id):
        for r in _BATCHES[batch_id]["requests"]:
            p = r["params"]
            assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", r["custom_id"]), r["custom_id"]
            assert "temperature" not in p
            assert ("thinking" not in p) if p["model"] == "claude-opus-5-5" else p["thinking"] == {"type": "adaptive"}
            if _rng.random() < 0.005:
                yield _O(custom_id=r["custom_id"], result=_O(type="errored"))
                continue
            msg = _O(model=p["model"], stop_reason="end_turn",
                     usage=_O(input_tokens=120, output_tokens=_rng.randint(100, 500)),
                     content=[_O(type="thinking", thinking="..."), _O(type="text", text=_answer(p))])
            yield _O(custom_id=r["custom_id"], result=_O(type="succeeded", message=msg))


class _Messages:
    batches = _Batches()


class _Models:
    def retrieve(self, model_id):
        return _O(id=model_id)


class Anthropic:
    def __init__(self, max_retries=2, timeout=None):
        self.messages, self.models = _Messages(), _Models()
