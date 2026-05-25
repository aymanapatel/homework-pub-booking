# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

The clearest planner handoff decision is in Ex7 ticket `tk_23af86b0`. Its `raw_output.json` contains subgoal `sg_3`: `"Submit the revised booking proposal with the adjusted party size"`, with `"assigned_half": "structured"`. That is the planner deciding that the revised proposal should leave the loop half and be validated by the structured half rather than being handled by another free-form tool call.

The signal that caused this decision was the previous structured rejection. In `session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/logs/trace.jsonl`, line 7 shows Rasa normalising the first proposal as `venue_id: "haymarket_tap"` with `party_size: 12`. Line 8 then records `structured.escalated` with the reason `"party_too_large"`, and line 9 records the bridge moving from `structured` back to `loop` with that rejection reason. When round 2 starts, line 11 shows the planner prompt carrying the exact signal forward: `"The structured half rejected the previous proposal. Reason: sorry, we can't accept this booking. reason: party_too_large. Produce an alternative."`

So the handoff was not arbitrary. The loop half re-planned after a deterministic structured rejection, then assigned the final revised proposal to the structured half because acceptance required the booking rules to be checked again.


### Citation

- [raw_output.json](../session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/logs/tickets/tk_23af86b0/raw_output.json)
- [trace.jsonl](../session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/logs/trace.jsonl)

---

## Q2 — Dataflow integrity catch

### Your answer

In `sess_3144b5ed6233`, the final Ex5 flyer passed the dataflow check: the trace shows successful `venue_search`, `get_weather`, and `calculate_cost` calls before `generate_flyer`, and the flyer facts match those outputs.

A plausible failure this check would catch is a subtle cost fabrication in that same flyer. To construct it, take `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/workspace/flyer.html` and change only the total from `£540` to `£560`, leaving the venue, date, weather, and deposit text unchanged. A human reviewer could easily miss this because `£560` is close to the real total and still looks like a reasonable catering cost.

However, the trace records `calculate_cost(haymarket_tap, 6): total £540, deposit £0`, so `_TOOL_CALL_LOG` would contain `540`, not `560`. `verify_dataflow` would extract `£560` from the edited flyer, fail to find it in any source tool output, and return it as an unverified fact. The important point is that the checker does not ask whether a number looks plausible; it asks whether the number was actually produced by a tool.

### Citation

- `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/logs/trace.jsonl`, lines 3-7
- `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/workspace/flyer.html`

---

## Q3 — Removing one framework primitive

### Your answer

The first production failure I would expect is a booking being marked complete even though the structured validator never actually confirmed it, most likely during an external Rasa outage or timeout. The business impact is serious: staff would think a table was booked, but the pub's rule system would not have accepted or persisted the booking.

The one sovereign-agent primitive I would rely on first is the ticket state machine. In the successful Ex7 run, the trace makes the state progression auditable: line 5 moves from `loop` to `structured`, line 9 moves from `structured` back to `loop` after `party_too_large`, line 15 moves from `loop` to `structured` again, and only after `structured.completed` at line 18 does line 19 move from `structured` to `complete`. That ordering is the property I would want in production.

If Rasa timed out or returned an error, the expected failure mode would be a missing `structured.completed` event before completion. The ticket state machine should surface that because there would be no valid transition from the structured half to `complete`; the ticket should remain escalated, failed, or retryable instead. I would monitor for any completed session whose ticket history lacks a structured completion immediately before the final state change.

### Citation

- `session_logs/examples/ex7-handoff-bridge/sess_11d93c3e817e/logs/trace.jsonl`, lines 5, 9, 15, 18, and 19
