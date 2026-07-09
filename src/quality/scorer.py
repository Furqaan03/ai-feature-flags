"""LLM-as-judge quality scoring for AI feature outputs (1-5)."""
from __future__ import annotations

import json

from openai import OpenAI

_JUDGE_PROMPT = """Score the quality of this AI feature output 1-5 for the given input.
5 = excellent, 1 = poor/unhelpful/wrong. Respond as JSON: {"score": 1-5, "reason": "one sentence"}."""


def score_output(feature_input: str, feature_output: str, client: OpenAI | None = None) -> float:
    client = client or OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _JUDGE_PROMPT},
            {"role": "user", "content": f"Input: {feature_input}\nOutput: {feature_output}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    parsed = json.loads(resp.choices[0].message.content or "{}")
    return float(parsed.get("score", 3))
