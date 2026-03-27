import asyncio
import logging
import os
import sys

from shared.config import bootstrap
bootstrap()

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from opentelemetry import trace

load_dotenv()

from orchestrator.agent import art_appraisal_pipeline
from otel_setup import setup_otel_tracing, setup_otel_logging, otel_log, OTEL_LOG_PATH
from display import (
    C, agent_label, colored_label, banner, ruler,
    print_agent_start, print_handoff, print_intermediate,
    print_parallel_start, print_parallel_agent_active, print_parallel_complete,
    AGENT_META,
)

tracer      = setup_otel_tracing()
otel_logger = setup_otel_logging()

APP_NAME = "art_appraisal_swarm"
USER_ID  = "learner_001"
session_service = InMemorySessionService()

SPECIALISTS = {"style_analyst", "provenance_specialist", "market_valuator"}


def extract_parts(event):
    texts, calls, responses = [], [], []
    if not (event.content and event.content.parts):
        return texts, calls, responses
    for part in event.content.parts:
        if getattr(part, "function_call", None):
            calls.append(part.function_call)
        elif getattr(part, "function_response", None):
            responses.append(part.function_response)
        elif getattr(part, "text", None):
            texts.append(part.text)
    return texts, calls, responses


async def run_appraisal_chat() -> None:
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    otel_log(otel_logger, logging.INFO, "Session created",
             session_id=session.id, user_id=USER_ID)

    runner = Runner(
        agent=art_appraisal_pipeline,
        app_name=APP_NAME,
        session_service=session_service,
    )

    banner("Art Appraisal Swarm  --  Google ADK + A2A Protocol")
    print(f"\n  Pipeline architecture (bias-free swarm voting):")
    print(f"    {colored_label('art_appraisal_pipeline')}")
    print(f"      +-- {colored_label('parallel_evaluation')} (Stage 1)")
    for name in ("style_analyst", "provenance_specialist", "market_valuator"):
        print(f"      |     +-- {colored_label(name)}")
    print(f"      +-- {colored_label('synthesis_agent')} (Stage 2)")
    print()
    print(f"  OTEL logs -> {OTEL_LOG_PATH}   (tail -f otel.log)")
    print()
    print("  Try: 'Appraise a Monet Water Lilies, oil on canvas, 80x100cm,")
    print("        painted in 1906. Acquired via Christie's London 1989 (Lot 42).")
    print("        Condition good, minor craquelure. Country of origin: France.'")
    print("\n  Type 'quit' to exit.")
    ruler()

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        message = types.Content(role="user", parts=[types.Part(text=user_input)])
        otel_log(otel_logger, logging.INFO, "User message",
                 session_id=session.id, preview=user_input[:120])

        banner("NEW REQUEST  -->  PIPELINE START")

        prev_author            = None
        event_count            = 0
        in_parallel            = False
        parallel_banner_shown  = False
        synthesis_header_shown = False
        specialist_texts:   dict[str, str]       = {}
        specialist_buffers: dict[str, list[str]] = {}

        with tracer.start_as_current_span(
            "appraisal_request",
            attributes={"session.id": session.id, "query.preview": user_input[:200]},
        ) as root_span:

            async for event in runner.run_async(
                session_id=session.id,
                user_id=USER_ID,
                new_message=message,
            ):
                event_count += 1
                author = getattr(event, "author", None) or "unknown"

                if author != prev_author and prev_author in SPECIALISTS:
                    if prev_author not in specialist_texts:
                        buffered = "\n".join(specialist_buffers.get(prev_author, []))
                        if buffered:
                            specialist_texts[prev_author] = buffered
                            otel_log(otel_logger, logging.INFO, "Specialist report (transition)",
                                     agent=prev_author, session_id=session.id,
                                     length=len(buffered))

                if author in SPECIALISTS and not in_parallel:
                    in_parallel = True
                    if not parallel_banner_shown:
                        print_parallel_start()
                        parallel_banner_shown = True
                        otel_log(otel_logger, logging.INFO, "Parallel stage started",
                                 session_id=session.id)

                if author == "synthesis_agent" and in_parallel:
                    in_parallel = False
                    print_parallel_complete(specialist_texts)
                    print_handoff("parallel_evaluation", "synthesis_agent")
                    otel_log(otel_logger, logging.INFO, "Parallel stage complete",
                             specialists_completed=len(specialist_texts),
                             session_id=session.id)
                    prev_author = author

                if author != prev_author:
                    if prev_author is None:
                        if author not in SPECIALISTS:
                            print_agent_start(author)
                        otel_log(otel_logger, logging.INFO, "Agent start",
                                 agent=author, session_id=session.id)
                    elif in_parallel:
                        print_parallel_agent_active(author)
                        otel_log(otel_logger, logging.INFO, "Parallel agent active",
                                 agent=author, session_id=session.id)
                    elif author != "synthesis_agent":
                        print_handoff(prev_author, author)
                        otel_log(otel_logger, logging.INFO, "Handoff",
                                 agent_from=prev_author, agent_to=author,
                                 session_id=session.id)
                    prev_author = author

                texts, fn_calls, fn_responses = extract_parts(event)

                for fc in fn_calls:
                    otel_log(otel_logger, logging.DEBUG, "Tool call",
                             agent=author, tool=fc.name, session_id=session.id)
                for fr in fn_responses:
                    otel_log(otel_logger, logging.DEBUG, "Tool result",
                             agent=author, tool=fr.name, session_id=session.id)

                if author in SPECIALISTS and texts:
                    specialist_buffers.setdefault(author, []).extend(texts)

                if author == "synthesis_agent":
                    if texts:
                        if not synthesis_header_shown:
                            synthesis_header_shown = True
                            banner(
                                f"MAJORITY VOTE + FINAL APPRAISAL  --  {agent_label('synthesis_agent')}",
                                "synthesis_agent",
                            )
                        for t in texts:
                            if t.strip():
                                print(C("synthesis_agent", f"  {t}"), flush=True)
                    if event.is_final_response():
                        if synthesis_header_shown:
                            banner("END OF APPRAISAL", "synthesis_agent")
                            otel_log(otel_logger, logging.INFO, "Synthesis complete",
                                     agent=author, session_id=session.id,
                                     total_events=event_count)
                            root_span.set_attribute("response.length", event_count)

                elif author in SPECIALISTS:
                    for t in texts:
                        if t.strip():
                            print_intermediate(author, t)
                    if event.is_final_response() and author not in specialist_texts:
                        report = "\n".join(texts) or "\n".join(
                            specialist_buffers.get(author, [])
                        )
                        if report:
                            specialist_texts[author] = report
                            otel_log(otel_logger, logging.INFO, "Specialist report ready",
                                     agent=author, session_id=session.id,
                                     length=len(report))

                else:
                    for t in texts:
                        if t.strip():
                            print_intermediate(author, t)


if __name__ == "__main__":
    if not os.environ.get("NOVA_API_KEY"):
        print("ERROR: Set NOVA_API_KEY in your .env file (copy .env.example)")
        sys.exit(1)
    asyncio.run(run_appraisal_chat())
