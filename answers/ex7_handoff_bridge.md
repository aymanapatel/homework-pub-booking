# Ex7 — Handoff bridge

## Your answer

The Ex7 bridge run in `session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/` completed the required loop-to-structured-to-loop-to-structured round trip. Round 1 began in the loop half at trace line 1. The loop searched Haymarket for a party of 12 at line 4 and the bridge recorded the forward transition from `loop` to `structured` at line 5. Rasa then normalised the attempted `haymarket_tap` booking with `party_size` 12 at line 7 and rejected it at line 8 with `party_too_large`.

The bridge preserved that rejection as a reverse handoff signal. Line 9 records `session.state_changed` from `structured` back to `loop` with the rejection reason included. Round 2 starts at line 10, and the planner prompt at line 11 explicitly contains the structured rejection and asks for an alternative. After additional venue search calls at lines 13-14, the bridge hands off again at line 15. This time the structured half normalises a `royal_oak` booking at line 17, completes it with booking reference `BK-9B8DBC29` at line 18, and the bridge marks the session complete at line 19. The trace therefore shows both forward context transfer and reverse rejection handling within two rounds.

## Citations

- `session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/logs/trace.jsonl`, lines 1-19 — round starts, handoffs, rejection, and completion
- `starter/handoff_bridge/bridge.py` — `HandoffBridge.run` and helpers
- `starter/handoff_bridge/integrity.py` — `verify_dataflow`
