"""Intermediate NL evaluation (reasoning path).

ADK ships criteria that touch intermediate steps in two main ways:

- ``hallucinations_v1`` with ``evaluate_intermediate_nl_responses: true`` — LLM-judged
  grounding of intermediate natural-language segments against tool/context (see
  ``evaluation/test_config.json``).
- Goldens: under each invocation, set ``intermediate_data.intermediate_responses``
  as ADK-native ``[author, parts]`` pairs (see ``evaluation/lib/golden_io.py``); keep
  them in sync with ``adk web`` exports when possible.

There is no separate Jaeger signal for “semantic match to golden intermediate text”;
batch **quality** lives in **ADK eval** + CI artifacts, while Jaeger shows **distributed
runtime** spans (see root README / ``evaluation/README.md``).
"""
