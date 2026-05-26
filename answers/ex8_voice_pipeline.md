# Ex8 — Voice pipeline

## Your answer

The Ex8 traces show both the real voice-shaped path and the text fallback path logging the same audit events. In `session_logs/homework/ex8/sess_af6889a8c9c1/logs/trace.jsonl`, every user utterance is recorded as `voice.utterance_in` and every manager reply as `voice.utterance_out`, with `mode: "voice"`. The first turn transcribed a request for ten people at Haymarket Tap and the manager declined because the party was too large, suggesting Royal Oak or Bennet's Bar. When the user reduced the booking to eight people, the manager accepted, requested a contact number, collected date/time, accepted a `£95` deposit, and then closed politely.

The second session, `session_logs/homework/ex8/sess_14d720a6713c/`, shows the same pipeline in text mode. It records six turns, including a successful booking for three at `10PM tonight`, a contact number, an out-of-scope `"buy"` request, and a final `"bye"`. This confirms the implementation's important invariant: downstream grading can rely on `voice.utterance_in` and `voice.utterance_out` regardless of whether audio STT/TTS or text fallback was used. The manager persona also stayed inside the booking domain and enforced the expected capacity rule.

The upstream answer specifically calls out graceful degradation, which is part of the same design. `run_voice_mode` checks for `SPEECHMATICS_KEY` and voice dependencies before starting audio capture; if they are missing, it warns and falls back to `run_text_mode`. That keeps the trace contract stable: the transport may be `"voice"` or `"text"`, but every turn still has the same event pair and payload fields.

## Citations

- `session_logs/homework/ex8/sess_af6889a8c9c1/logs/trace.jsonl`, lines 1-12 — voice-mode utterance audit
- `session_logs/homework/ex8/sess_14d720a6713c/logs/trace.jsonl`, lines 1-12 — text-mode utterance audit
- `starter/voice_pipeline/voice_loop.py` — `run_voice_mode`
- `starter/voice_pipeline/manager_persona.py` — LLM-backed persona
