"""Ex6 — runner (reference solution).

Three modes:

  python -m starter.rasa_half.run          (mock, no services) → tier 1
  python -m starter.rasa_half.run --real   (assume Rasa is up)  → tier 2
  python -m starter.rasa_half.run --real --auto  (auto-spawn)    → tier 3

Tier 1 uses a stdlib mock that matches Rasa's HTTP shape. Students can
validate their normalise_booking_payload + structured_half code without
installing Rasa Pro or obtaining a license.

Tier 2 assumes Rasa is already running on localhost:5005 (rasa serve)
and localhost:5055 (actions). Students start these themselves in two
other terminals — this teaches the multi-process coordination pattern
that real agent systems use in production.

Tier 3 auto-spawns both Rasa processes via RasaHostLifecycle, runs the
scenario, and tears them down. Convenient for CI / demos but hides
what tier 2 teaches.
"""

from __future__ import annotations

import asyncio
import sys

from sovereign_agent._internal.paths import example_sessions_dir
from sovereign_agent.session.directory import create_session

from starter.rasa_half.structured_half import (
    RasaHostLifecycle,
    RasaStructuredHalf,
    spawn_mock_rasa,
)


async def run_scenario(real: bool, auto: bool) -> int:
    with example_sessions_dir("ex6-rasa-half", persist=real) as sessions_root:
        session = create_session(
            scenario="ex6-rasa",
            task="Confirm and resume bookings through the Rasa structured half.",
            sessions_dir=sessions_root,
        )
        print(f"📂 Session {session.session_id}")
        print(f"   dir: {session.directory}")

        rubric_cases = [
            (
                "confirm_booking valid",
                True,
                {
                    "action": "confirm_booking",
                    "venue_id": "Haymarket Tap",
                    "date": "25th April 2026",
                    "time": "7:30pm",
                    "party_size": "6",
                    "deposit": "£200",
                },
            ),
            (
                "resume_from_loop valid",
                True,
                {
                    "action": "resume_from_loop",
                    "venue_id": "Haymarket Tap",
                    "date": "25th April 2026",
                    "time": "7:30pm",
                    "party_size": "6",
                    "deposit": "£200",
                },
            ),
            (
                "reject party over cap",
                False,
                {
                    "action": "confirm_booking",
                    "venue_id": "Haymarket Tap",
                    "date": "25th April 2026",
                    "time": "8:00pm",
                    "party_size": "12",
                    "deposit": "£200",
                },
            ),
            (
                "reject deposit over cap",
                False,
                {
                    "action": "confirm_booking",
                    "venue_id": "Haymarket Tap",
                    "date": "25th April 2026",
                    "time": "8:30pm",
                    "party_size": "6",
                    "deposit": "£500",
                },
            ),
        ]

        async def run_rubric_cases(half: RasaStructuredHalf) -> list[tuple[str, bool, object]]:
            outcomes = []
            for label, expected_success, data in rubric_cases:
                result = await half.run(session, {"data": data})
                outcomes.append((label, expected_success, result))
            return outcomes

        if real and auto:
            # Tier 3 — auto-spawn.
            log_dir = session.logs_dir / "rasa"
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"   Rasa logs: {log_dir}")
            print(
                "   (tier 3 auto-spawn mode — the scenario spawns Rasa + action\n"
                "    server subprocesses, runs, then tears them down)"
            )
            async with RasaHostLifecycle(log_dir=log_dir) as rasa_url:
                print(f"   Rasa URL: {rasa_url}")
                half = RasaStructuredHalf(rasa_url=rasa_url, request_timeout_s=30.0)
                outcomes = await run_rubric_cases(half)

        elif real:
            # Tier 2 — assume Rasa is already running.
            print(
                "   (tier 2: assuming rasa-actions + rasa-serve are already\n"
                "    running in two other terminals. If you see a connection\n"
                "    error below, run `make ex6-help` for the setup recipe.)"
            )
            rasa_url = "http://localhost:5005/webhooks/rest/webhook"
            print(f"   Rasa URL: {rasa_url}")
            half = RasaStructuredHalf(rasa_url=rasa_url, request_timeout_s=30.0)
            outcomes = await run_rubric_cases(half)

        else:
            # Tier 1 — mock.
            print("   (tier 1: stdlib mock Rasa on :5905 — no license needed)")
            server, _thread, mock_url = spawn_mock_rasa(port=5905)
            try:
                print(f"   Mock URL: {mock_url}")
                half = RasaStructuredHalf(rasa_url=mock_url)
                outcomes = await run_rubric_cases(half)
            finally:
                server.shutdown()

        print("\nStructured half outcomes:")
        all_expected = True
        for label, expected_success, result in outcomes:
            passed = result.success is expected_success
            all_expected = all_expected and passed
            marker = "✓" if passed else "✗"
            print(f"  {marker} {label}: {result.next_action}")
            print(f"    summary: {result.summary}")
            print(f"    output:  {result.output}")

        if real:
            print(f"\n📂 Session artifacts: {session.directory}")
            print(f"📜 Narrate this run:   make narrate SESSION={session.session_id}")

        return 0 if all_expected else 1


def main() -> None:
    real = "--real" in sys.argv
    auto = "--auto" in sys.argv
    if auto and not real:
        print("✗ --auto requires --real", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(run_scenario(real=real, auto=auto)))


if __name__ == "__main__":
    main()
