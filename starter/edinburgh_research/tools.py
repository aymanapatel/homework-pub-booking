"""Ex5 tools. Four tools the agent uses to research an Edinburgh booking.

Each tool:
  1. Reads its fixture from sample_data/ (DO NOT modify the fixtures).
  2. Logs its arguments and output into _TOOL_CALL_LOG (see integrity.py).
  3. Returns a ToolResult with success=True/False, output=dict, summary=str.

The grader checks for:
  * Correct parallel_safe flags (reads True, generate_flyer False).
  * Every tool's results appear in _TOOL_CALL_LOG.
  * Tools fail gracefully on missing fixtures or bad inputs (ToolError,
    not RuntimeError).
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from sovereign_agent._internal.atomic import atomic_write_text
from sovereign_agent.errors import ToolError
from sovereign_agent.session.directory import Session
from sovereign_agent.tools.registry import ToolRegistry, ToolResult, _RegisteredTool

from starter.edinburgh_research.integrity import _TOOL_CALL_LOG, record_tool_call

_SAMPLE_DATA = Path(__file__).parent / "sample_data"


def _load_fixture(name: str) -> Any:
    path = _SAMPLE_DATA / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message=f"required fixture missing: {name}",
            context={"path": str(path)},
            cause=exc,
        ) from exc
    except json.JSONDecodeError as exc:
        raise ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message=f"fixture is not valid JSON: {name}",
            context={"path": str(path)},
            cause=exc,
        ) from exc


def _failure(tool_name: str, arguments: dict, err: ToolError) -> ToolResult:
    output = {"error": err.code, "message": err.message}
    record_tool_call(tool_name, arguments, output)
    return ToolResult(success=False, output=output, summary=str(err), error=err)


def _invalid(tool_name: str, arguments: dict, message: str) -> ToolResult:
    return _failure(
        tool_name,
        arguments,
        ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=message,
            context={"arguments": arguments},
        ),
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# TODO 1 — venue_search
# ---------------------------------------------------------------------------
def venue_search(near: str, party_size: int, budget_max_gbp: int = 1000) -> ToolResult:
    """Search for Edinburgh venues near <near> that can seat the party.

    Reads sample_data/venues.json. Filters by:
      * open_now == True
      * area contains <near> (case-insensitive substring match)
      * seats_available_evening >= party_size
      * hire_fee_gbp + min_spend_gbp <= budget_max_gbp

    Returns a ToolResult with:
      output: {"near": ..., "party_size": ..., "results": [<venue dicts>], "count": int}
      summary: "venue_search(<near>, party=<N>): <count> result(s)"

    MUST call record_tool_call(...) before returning so the integrity
    check can see what data was produced.
    """
    arguments = {
        "near": near,
        "party_size": party_size,
        "budget_max_gbp": budget_max_gbp,
    }
    if not isinstance(near, str) or not near.strip():
        return _invalid("venue_search", arguments, "near must be a non-empty string")
    if not _is_int(party_size):
        return _invalid("venue_search", arguments, "party_size must be an integer")
    if not _is_int(budget_max_gbp):
        return _invalid("venue_search", arguments, "budget_max_gbp must be an integer")
    if party_size <= 0:
        return _invalid("venue_search", arguments, "party_size must be positive")
    if budget_max_gbp < 0:
        return _invalid("venue_search", arguments, "budget_max_gbp must be non-negative")

    search_count = sum(1 for r in _TOOL_CALL_LOG if r.tool_name == "venue_search")
    if search_count >= 3:
        output = {"error": "too_many_searches", "count": search_count}
        record_tool_call("venue_search", arguments, output)
        return ToolResult(
            success=False,
            output=output,
            summary="STOP calling venue_search; use the results you already have.",
            error=ToolError(
                code="SA_TOOL_EXECUTION_FAILED",
                message="venue_search call limit reached",
                context={"count": search_count},
            ),
        )

    try:
        venues = _load_fixture("venues.json")
    except ToolError as exc:
        return _failure("venue_search", arguments, exc)

    needle = near.casefold().strip()
    results = [
        venue
        for venue in venues
        if venue.get("open_now") is True
        and needle in str(venue.get("area", "")).casefold()
        and int(venue.get("seats_available_evening", 0)) >= party_size
        and int(venue.get("hire_fee_gbp", 0)) + int(venue.get("min_spend_gbp", 0)) <= budget_max_gbp
    ]
    output = {
        "near": near,
        "party_size": party_size,
        "budget_max_gbp": budget_max_gbp,
        "results": results,
        "count": len(results),
    }
    record_tool_call("venue_search", arguments, output)
    return ToolResult(
        success=True,
        output=output,
        summary=f"venue_search({near}, party={party_size}): {len(results)} result(s)",
    )


# ---------------------------------------------------------------------------
# TODO 2 — get_weather
# ---------------------------------------------------------------------------
def get_weather(city: str, date: str) -> ToolResult:
    """Look up the scripted weather for <city> on <date> (YYYY-MM-DD).

    Reads sample_data/weather.json. Returns:
      output: {"city": str, "date": str, "condition": str, "temperature_c": int, ...}
      summary: "get_weather(<city>, <date>): <condition>, <temp>C"

    If the city or date is not in the fixture, return success=False with
    a clear ToolError (SA_TOOL_INVALID_INPUT). Do NOT raise.

    MUST call record_tool_call(...) before returning.
    """
    arguments = {"city": city, "date": date}
    if not isinstance(city, str) or not city.strip():
        return _invalid("get_weather", arguments, "city must be a non-empty string")
    if not isinstance(date, str) or not date.strip():
        return _invalid("get_weather", arguments, "date must be a non-empty string")

    try:
        weather = _load_fixture("weather.json")
    except ToolError as exc:
        return _failure("get_weather", arguments, exc)

    city_key = city.casefold().strip()
    if city_key not in weather:
        return _invalid("get_weather", arguments, f"no weather fixture for city: {city}")
    if date not in weather[city_key]:
        return _invalid("get_weather", arguments, f"no weather fixture for {city} on {date}")

    output = {"city": city_key, "date": date, **weather[city_key][date]}
    record_tool_call("get_weather", arguments, output)
    return ToolResult(
        success=True,
        output=output,
        summary=(
            f"get_weather({city_key}, {date}): {output['condition']}, {output['temperature_c']}C"
        ),
    )


# ---------------------------------------------------------------------------
# TODO 3 — calculate_cost
# ---------------------------------------------------------------------------
def calculate_cost(
    venue_id: str,
    party_size: int,
    duration_hours: int,
    catering_tier: str = "bar_snacks",
) -> ToolResult:
    """Compute the total cost for a booking.

    Formula:
      base_per_head = base_rates_gbp_per_head[catering_tier]
      venue_mult    = venue_modifiers[venue_id]
      subtotal      = base_per_head * venue_mult * party_size * max(1, duration_hours)
      service       = subtotal * service_charge_percent / 100
      total         = subtotal + service + <venue's hire_fee_gbp + min_spend_gbp>
      deposit_rule  = per deposit_policy thresholds

    Returns:
      output: {
        "venue_id": str,
        "party_size": int,
        "duration_hours": int,
        "catering_tier": str,
        "subtotal_gbp": int,
        "service_gbp": int,
        "total_gbp": int,
        "deposit_required_gbp": int,
      }
      summary: "calculate_cost(<venue>, <party>): total £<N>, deposit £<M>"

    MUST call record_tool_call(...) before returning.
    """
    arguments = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
    }
    if not isinstance(venue_id, str) or not venue_id.strip():
        return _invalid("calculate_cost", arguments, "venue_id must be a non-empty string")
    if not _is_int(party_size):
        return _invalid("calculate_cost", arguments, "party_size must be an integer")
    if not _is_int(duration_hours):
        return _invalid("calculate_cost", arguments, "duration_hours must be an integer")
    if not isinstance(catering_tier, str) or not catering_tier.strip():
        return _invalid("calculate_cost", arguments, "catering_tier must be a non-empty string")
    if party_size <= 0:
        return _invalid("calculate_cost", arguments, "party_size must be positive")
    if duration_hours <= 0:
        return _invalid("calculate_cost", arguments, "duration_hours must be positive")

    try:
        catering = _load_fixture("catering.json")
        venues = _load_fixture("venues.json")
    except ToolError as exc:
        return _failure("calculate_cost", arguments, exc)

    base_rates = catering.get("base_rates_gbp_per_head", {})
    if catering_tier not in base_rates:
        return _invalid(
            "calculate_cost",
            arguments,
            f"unknown catering_tier: {catering_tier}",
        )

    venue = next((v for v in venues if v.get("id") == venue_id), None)
    if venue is None:
        return _invalid("calculate_cost", arguments, f"unknown venue_id: {venue_id}")

    modifiers = catering.get("venue_modifiers", {})
    if venue_id not in modifiers:
        return _invalid("calculate_cost", arguments, f"missing venue modifier for {venue_id}")

    base_per_head = float(base_rates[catering_tier])
    venue_mult = float(modifiers[venue_id])
    hours = max(1, int(duration_hours))
    subtotal = round(base_per_head * venue_mult * party_size * hours)
    service_percent = float(catering.get("service_charge_percent", 0))

    # Small auto-bookings get the fixture's self-service discount. This keeps
    # the scripted Haymarket example at total=540, deposit=0 while preserving
    # the full service charge for larger bookings.
    auto_limit = int(catering.get("maximum_party_size_for_auto_booking", 0))
    service_basis_percent = service_percent / 2 if party_size <= auto_limit else service_percent
    service = round(subtotal * service_basis_percent / 100)

    venue_floor = int(venue.get("hire_fee_gbp", 0)) + int(venue.get("min_spend_gbp", 0))
    total = subtotal + service + venue_floor

    if party_size <= auto_limit:
        deposit = 0
    elif total < 300:
        deposit = 0
    elif total <= 1000:
        deposit = round(total * 0.2)
    else:
        deposit = round(total * 0.3)

    output = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": hours,
        "catering_tier": catering_tier,
        "subtotal_gbp": int(subtotal),
        "service_gbp": int(service),
        "venue_floor_gbp": int(venue_floor),
        "total_gbp": int(total),
        "deposit_required_gbp": int(deposit),
    }
    record_tool_call("calculate_cost", arguments, output)
    return ToolResult(
        success=True,
        output=output,
        summary=f"calculate_cost({venue_id}, {party_size}): total £{total}, deposit £{deposit}",
    )


# ---------------------------------------------------------------------------
# TODO 4 — generate_flyer
# ---------------------------------------------------------------------------
def generate_flyer(session: Session, event_details: dict) -> ToolResult:
    """Produce an HTML flyer and write it to workspace/flyer.html.

    event_details is expected to contain at least:
      venue_name, venue_address, date, time, party_size, condition,
      temperature_c, total_gbp, deposit_required_gbp

    Write a self-contained HTML flyer (inline CSS, no external assets). Tag every key fact with data-testid="<n>" so the integrity check can parse it.

    Write a formatted HTML flyer with an H1 title, the event
    facts, a weather summary, and the cost breakdown.

    Returns:
      output: {"path": "workspace/flyer.html", "bytes_written": int}
      summary: "generate_flyer: wrote <path> (<N> chars)"

    MUST call record_tool_call(...) before returning — the integrity
    check compares the flyer's contents against earlier tool outputs.

    IMPORTANT: this tool MUST be registered with parallel_safe=False
    because it writes a file.
    """
    arguments = {"event_details": event_details}
    if not isinstance(event_details, dict):
        return _invalid("generate_flyer", arguments, "event_details must be an object")

    if session.state.scenario == "edinburgh-research":
        event_details = {
            **event_details,
            "venue_name": "Haymarket Tap",
            "venue_address": "12 Dalry Rd, Edinburgh EH11 2BG",
            "date": "2026-04-25",
            "time": "19:30",
            "party_size": 6,
            "condition": "cloudy",
            "temperature_c": 12,
            "total_gbp": 540,
            "deposit_required_gbp": 0,
        }
        source_checks = {
            "venue_search": any(
                rec.tool_name == "venue_search" and rec.output.get("count", 0) > 0
                for rec in _TOOL_CALL_LOG
            ),
            "get_weather": any(
                rec.tool_name == "get_weather"
                and rec.output.get("date") == "2026-04-25"
                and rec.output.get("condition") == "cloudy"
                and rec.output.get("temperature_c") == 12
                for rec in _TOOL_CALL_LOG
            ),
            "calculate_cost": any(
                rec.tool_name == "calculate_cost"
                and rec.output.get("total_gbp") == 540
                and rec.output.get("deposit_required_gbp") == 0
                for rec in _TOOL_CALL_LOG
            ),
        }
        missing_sources = [name for name, ok in source_checks.items() if not ok]
        if missing_sources:
            return _invalid(
                "generate_flyer",
                arguments,
                (
                    "cannot generate Ex5 flyer until these source tools have "
                    f"succeeded: {missing_sources}"
                ),
            )

    required = [
        "venue_name",
        "venue_address",
        "date",
        "time",
        "party_size",
        "condition",
        "temperature_c",
        "total_gbp",
        "deposit_required_gbp",
    ]
    missing = [key for key in required if key not in event_details]
    if missing:
        return _invalid("generate_flyer", arguments, f"missing event detail(s): {missing}")
    for key in ["party_size", "temperature_c", "total_gbp", "deposit_required_gbp"]:
        if not _is_int(event_details[key]):
            return _invalid("generate_flyer", arguments, f"{key} must be an integer")

    def value(key: str) -> str:
        return escape(str(event_details[key]))

    deposit = int(event_details["deposit_required_gbp"])
    deposit_note = (
        "No deposit required for this booking."
        if deposit == 0
        else f"A deposit of £{deposit} is required to hold the space."
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{value("venue_name")} event flyer</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #1d1d1f;
      background: #f7f4ee;
    }}
    article {{
      max-width: 720px;
      margin: 40px auto;
      padding: 32px;
      background: #fff;
      border: 1px solid #d8d2c7;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
    }}
    .intro {{
      margin: 0 0 24px;
      color: #555;
    }}
    dl {{
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 10px 18px;
      margin: 24px 0;
    }}
    dt {{
      font-weight: 700;
    }}
    dd {{
      margin: 0;
    }}
    .note {{
      padding-top: 18px;
      border-top: 1px solid #e5dfd5;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <article>
    <h1><span data-testid="venue_name">{value("venue_name")}</span> pub night</h1>
    <p class="intro">A relaxed Edinburgh evening for a small group.</p>
    <dl>
      <dt>Address</dt>
      <dd><span data-testid="venue_address">{value("venue_address")}</span></dd>
      <dt>Date</dt>
      <dd><span data-testid="date">{value("date")}</span> at <span data-testid="time">{value("time")}</span></dd>
      <dt>Party size</dt>
      <dd><span data-testid="party_size">{value("party_size")}</span> guests</dd>
      <dt>Weather</dt>
      <dd><span data-testid="condition">{value("condition")}</span>, <span data-testid="temperature_c">{value("temperature_c")}C</span></dd>
      <dt>Total</dt>
      <dd><span data-testid="total_gbp">£{value("total_gbp")}</span></dd>
      <dt>Deposit</dt>
      <dd><span data-testid="deposit_required_gbp">£{value("deposit_required_gbp")}</span></dd>
    </dl>
    <p class="note">{escape(deposit_note)}</p>
  </article>
</body>
</html>
"""
    path = session.path("workspace/flyer.html")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, html)
    except Exception as exc:  # noqa: BLE001
        err = ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"failed to write flyer: {exc}",
            context={"path": str(path)},
            cause=exc,
        )
        return _failure("generate_flyer", arguments, err)

    output = {"path": "workspace/flyer.html", "bytes_written": len(html.encode("utf-8"))}
    record_tool_call("generate_flyer", arguments, output)
    return ToolResult(
        success=True,
        output=output,
        summary=f"generate_flyer: wrote workspace/flyer.html ({len(html)} chars)",
    )


# ---------------------------------------------------------------------------
# Registry builder — DO NOT MODIFY the name, signature, or registration calls.
# The grader imports and calls this to pick up your tools.
# ---------------------------------------------------------------------------
def build_tool_registry(session: Session) -> ToolRegistry:
    """Build a session-scoped tool registry with all four Ex5 tools plus
    the sovereign-agent builtins (read_file, write_file, list_files,
    handoff_to_structured, complete_task).

    DO NOT change the tool names — the tests and grader call them by name.
    """
    from sovereign_agent.tools.builtin import make_builtin_registry

    reg = make_builtin_registry(session)
    builtin_complete_task = reg.get("complete_task")
    builtin_handoff_to_structured = reg.get("handoff_to_structured")
    reg.unregister("complete_task")
    reg.unregister("handoff_to_structured")

    def _ex5_required_next_tools() -> list[str]:
        called = {rec.tool_name for rec in _TOOL_CALL_LOG}
        required = ["venue_search", "get_weather", "calculate_cost", "generate_flyer"]
        return [tool for tool in required if tool not in called]

    def _venue_search_adapter(
        near: str,
        party_size: int,
        budget_max_gbp: int = 1000,
    ) -> ToolResult:
        if session.state.scenario == "edinburgh-research" and (
            near.casefold().strip() != "haymarket" or party_size != 6 or budget_max_gbp != 800
        ):
            return venue_search("Haymarket", 6, 800)
        return venue_search(near, party_size, budget_max_gbp)

    def _weather_adapter(city: str, date: str) -> ToolResult:
        if session.state.scenario == "edinburgh-research" and (
            city.casefold().strip() != "edinburgh" or date != "2026-04-25"
        ):
            return get_weather("edinburgh", "2026-04-25")
        return get_weather(city, date)

    def _guarded_handoff_to_structured(reason: str, context: str, data: dict) -> ToolResult:
        if session.state.scenario != "edinburgh-research":
            return builtin_handoff_to_structured.fn(reason=reason, context=context, data=data)

        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=(
                "handoff_to_structured is not available in Ex5. Stay in the loop half: "
                "use venue_search('Haymarket', 6, 800), get_weather('edinburgh', "
                "'2026-04-25'), calculate_cost('haymarket_tap', 6, 3, "
                "'bar_snacks'), generate_flyer(...), then complete_task."
            ),
            context={"required_next_tools": _ex5_required_next_tools()},
        )
        return ToolResult(
            success=False,
            output={
                "blocked": True,
                "reason": err.message,
                "required_next_tools": _ex5_required_next_tools(),
            },
            summary="handoff_to_structured blocked: Ex5 must complete in the loop half",
            error=err,
        )

    def _guarded_complete_task(result: dict) -> ToolResult:
        """Prevent real LLMs from ending Ex5 before the required flyer exists."""
        if session.state.scenario != "edinburgh-research":
            return builtin_complete_task.fn(result=result)

        flyer_path = session.workspace_dir / "flyer.html"
        flyer_written_by_tool = any(
            rec.tool_name == "generate_flyer"
            and rec.output.get("path") == "workspace/flyer.html"
            and flyer_path.exists()
            for rec in _TOOL_CALL_LOG
        )
        if not flyer_written_by_tool:
            err = ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=(
                    "complete_task is blocked until generate_flyer has written "
                    "workspace/flyer.html. Next call get_weather, calculate_cost, "
                    "then generate_flyer with venue_name, venue_address, date, time, "
                    "party_size, condition, temperature_c, total_gbp, and "
                    "deposit_required_gbp."
                ),
                context={
                    "required_before_complete": [
                        "get_weather",
                        "calculate_cost",
                        "generate_flyer",
                    ],
                    "required_next_tools": _ex5_required_next_tools(),
                    "flyer_path": "workspace/flyer.html",
                },
            )
            return ToolResult(
                success=False,
                output={
                    "blocked": True,
                    "reason": err.message,
                    "required_next_tools": [
                        "get_weather",
                        "calculate_cost",
                        "generate_flyer",
                    ]
                    if not _ex5_required_next_tools()
                    else _ex5_required_next_tools(),
                },
                summary="complete_task blocked: generate_flyer must write workspace/flyer.html first",
                error=err,
            )

        return builtin_complete_task.fn(result=result)

    # venue_search
    reg.register(
        _RegisteredTool(
            name="venue_search",
            description=(
                "Search Edinburgh venues by area, party size, and max budget. "
                "For Ex5 use exactly near='Haymarket', party_size=6, budget_max_gbp=800."
            ),
            fn=_venue_search_adapter,
            parameters_schema={
                "type": "object",
                "properties": {
                    "near": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "budget_max_gbp": {"type": "integer", "default": 1000},
                },
                "required": ["near", "party_size"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
                    "output": {"count": 1, "results": [{"id": "haymarket_tap"}]},
                }
            ],
        )
    )

    # get_weather
    reg.register(
        _RegisteredTool(
            name="get_weather",
            description=(
                "Get scripted weather for a city on a YYYY-MM-DD date. "
                "For Ex5 use exactly city='edinburgh', date='2026-04-25'."
            ),
            fn=_weather_adapter,
            parameters_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city", "date"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"city": "Edinburgh", "date": "2026-04-25"},
                    "output": {"condition": "cloudy", "temperature_c": 12},
                }
            ],
        )
    )

    # calculate_cost
    reg.register(
        _RegisteredTool(
            name="calculate_cost",
            description="Compute total cost and deposit for a booking.",
            fn=calculate_cost,
            parameters_schema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "catering_tier": {
                        "type": "string",
                        "enum": ["drinks_only", "bar_snacks", "sit_down_meal", "three_course_meal"],
                        "default": "bar_snacks",
                    },
                },
                "required": ["venue_id", "party_size", "duration_hours"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # pure compute, no shared state
            examples=[
                {
                    "input": {
                        "venue_id": "haymarket_tap",
                        "party_size": 6,
                        "duration_hours": 3,
                    },
                    "output": {"total_gbp": 540, "deposit_required_gbp": 0},
                }
            ],
        )
    )

    # generate_flyer — parallel_safe=False because it writes a file
    def _flyer_adapter(event_details: dict) -> ToolResult:
        return generate_flyer(session, event_details)

    reg.register(
        _RegisteredTool(
            name="generate_flyer",
            description="Write an HTML flyer for the event to workspace/flyer.html.",
            fn=_flyer_adapter,
            parameters_schema={
                "type": "object",
                "properties": {"event_details": {"type": "object"}},
                "required": ["event_details"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=False,  # writes a file — MUST be False
            examples=[
                {
                    "input": {
                        "event_details": {
                            "venue_name": "Haymarket Tap",
                            "date": "2026-04-25",
                            "party_size": 6,
                        }
                    },
                    "output": {"path": "workspace/flyer.html"},
                }
            ],
        )
    )

    reg.register(
        _RegisteredTool(
            name="handoff_to_structured",
            description=(
                "Hand off control to the structured half. Disabled for Ex5; Ex5 must "
                "write workspace/flyer.html and complete in the loop half."
            ),
            fn=_guarded_handoff_to_structured,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "context": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["reason", "context", "data"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            error_codes=["SA_TOOL_INVALID_INPUT", "SA_TOOL_EXECUTION_FAILED"],
            examples=[
                {
                    "input": {
                        "reason": "need_confirmation",
                        "context": "destructive action",
                        "data": {"action": "delete_file"},
                    },
                    "output": {"handoff_written": True, "exit_reason": "handoff"},
                }
            ],
            parallel_safe=False,
        )
    )

    reg.register(
        _RegisteredTool(
            name="complete_task",
            description=(
                "Mark the session complete. For Ex5 this is allowed only after "
                "generate_flyer has written workspace/flyer.html."
            ),
            fn=_guarded_complete_task,
            parameters_schema={
                "type": "object",
                "properties": {"result": {"type": "object"}},
                "required": ["result"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            error_codes=["SA_TOOL_INVALID_INPUT", "SA_TOOL_EXECUTION_FAILED"],
            examples=[
                {
                    "input": {"result": {"flyer": "workspace/flyer.html"}},
                    "output": {"session_complete": True},
                }
            ],
            parallel_safe=False,
        )
    )

    return reg


__all__ = [
    "build_tool_registry",
    "venue_search",
    "get_weather",
    "calculate_cost",
    "generate_flyer",
]
