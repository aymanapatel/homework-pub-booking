# Ex5 — Edinburgh research loop scenario

## Your answer

The Ex5 run in `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/` completed the required loop-half research flow and wrote the final HTML flyer. The trace shows the planner starting the task at line 1 and producing three subgoals at line 2. The executor then called the required tools with the assignment parameters: `venue_search(near="Haymarket", party_size=6, budget_max_gbp=800)` at line 3, `get_weather(city="edinburgh", date="2026-04-25")` at line 5, `calculate_cost(venue_id="haymarket_tap", party_size=6, duration_hours=3, catering_tier="bar_snacks")` at line 6, and `generate_flyer` at line 7.

The upstream answer emphasizes the same split between read-only research tools and the writer tool. In this local run, `venue_search`, `get_weather`, and `calculate_cost` are the fixture-backed research calls, while `generate_flyer` is the state-changing call that writes the final artifact. That matters because dataflow integrity should trust concrete tool outputs, not plausible prose.

The important behaviour is that the loop did not count the task as complete until the flyer existed. Line 4 records a failed early `complete_task` call: it was blocked because `generate_flyer` had not yet written `workspace/flyer.html`. After the flyer was generated with Haymarket Tap, cloudy 12C weather, total `£540`, and `£0` deposit, `complete_task` succeeded at line 8. The final artifact is `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/workspace/flyer.html`, which matches the tool outputs rather than invented values.

## Citations

- `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/logs/trace.jsonl`, lines 1-8 — tool call sequence
- `session_logs/examples/ex5-edinburgh-research/sess_3144b5ed6233/workspace/flyer.html` — the produced flyer
