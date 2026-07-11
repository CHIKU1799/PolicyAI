"""Mapping/extraction evaluation harness for PolicyAI.

A small gold set of fixture regulations + expected fields, and a scorer that
measures how well the extraction + mapping pipeline performs. Run live with
``python -m policyai_extraction.eval.run_eval`` (needs an LLM key); the scoring
functions in ``scoring.py`` are pure and unit-tested offline.
"""
