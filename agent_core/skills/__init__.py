"""Hermes-style skill layer: each tool = a spec + a deterministic verifier.

A skill folder contains:
  SKILL.md   — the contract (purpose, input schema, output schema, examples).
  run.py     — the deterministic implementation the agent's tool-call invokes.
  verify.py  — a deterministic verifier: given (input, output), assert the
               output satisfies the contract. No LLM in the verifier.

The agent (agent.py) may CHOOSE a skill; run.py EXECUTES it; verify.py CHECKS
it before the shell trusts the result. See ../../docs/IMPLEMENTATION.md.
"""
