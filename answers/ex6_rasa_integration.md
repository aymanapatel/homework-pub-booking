# Ex6 — Rasa structured half

## Your answer

The Ex6 session in `session_logs/examples/ex6-rasa-half/sess_2dff21c5be13/` demonstrates the structured half acting as the deterministic booking validator. On the happy path, the trace starts with `structured.called`, then normalises a `confirm_booking` payload for `haymarket_tap` into canonical fields: date `2026-04-25`, time `19:30`, `party_size` 6, `deposit_gbp` 200, duration 3, and catering tier `bar_snacks`. The next line records completion with booking reference `BK-7D401E9E`.

The upstream answer highlights the implementation path: raw loop data flows through `normalise_booking_payload`, becomes a Rasa-shaped message, is POSTed to the REST webhook, and is converted back into a `HalfResult`. That is visible in the local trace because every call has a `structured.normalised` event before completion or escalation. Network or validation failures are handled as structured outcomes rather than uncaught exceptions.

The same session also verifies resume behaviour. Lines 4-6 repeat the flow with action `resume_from_loop`, preserve the same booking details, and complete with the same reference. The rejection cases show why this belongs in the structured half rather than the open loop half: line 8 normalises a party of 12 and line 9 escalates with `party_too_large`; line 11 normalises a party of 6 with a `£500` deposit and line 12 escalates with `deposit_too_high`. That matches the implementation split: `normalise_booking_payload` canonicalises messy loop data before the HTTP call, while `RasaStructuredHalf.run` logs normalisation and converts Rasa accept/reject responses into `HalfResult` outcomes.

## Citations

- `session_logs/examples/ex6-rasa-half/sess_2dff21c5be13/logs/trace.jsonl`, lines 1-12 — normalised, completed, and escalated structured outcomes
- `starter/rasa_half/validator.py` — `normalise_booking_payload` and helpers
- `starter/rasa_half/structured_half.py` — `RasaStructuredHalf.run` and mock server
