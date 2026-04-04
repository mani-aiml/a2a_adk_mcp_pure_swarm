from shared.registry import (
    AGENT_COLORS, AGENT_META, SPECIALISTS, SPECIALIST_NAMES,
    RESET, BOLD,
)

WIDTH = 72


def C(agent: str, text: str) -> str:
    return f"{AGENT_COLORS.get(agent, BOLD)}{text}{RESET}"


def agent_label(name: str) -> str:
    if name in AGENT_META:
        title, loc = AGENT_META[name]
        return f"{title:<22} ({loc})"
    return name.upper()


def colored_label(name: str) -> str:
    return C(name, agent_label(name))


def ruler(char: str = "-", agent: str = "") -> None:
    print(C(agent, char * WIDTH) if agent else char * WIDTH)


def banner(text: str, agent: str = "") -> None:
    color = AGENT_COLORS.get(agent, BOLD)
    print(f"\n{color}{'=' * WIDTH}{RESET}")
    print(f"{color}  {text}{RESET}")
    print(f"{color}{'=' * WIDTH}{RESET}")


def print_agent_start(agent: str) -> None:
    color = AGENT_COLORS.get(agent, BOLD)
    print(f"\n{color}  ACTIVE: {agent_label(agent)}{RESET}")
    ruler("-", agent)


def print_handoff(from_agent: str, to_agent: str) -> None:
    to_color = AGENT_COLORS.get(to_agent, BOLD)
    w = WIDTH - 4
    print(f"\n{to_color}  +{'-' * w}+")
    print(f"  |  HANDOFF TO: {agent_label(to_agent):<{w - 14}}|")
    print(f"  |  FROM:       {agent_label(from_agent):<{w - 14}}|")
    print(f"  +{'-' * w}+{RESET}\n")


def print_intermediate(agent: str, text: str) -> None:
    if text.strip():
        print(C(agent, f"  {text.strip()}"))


def print_parallel_start() -> None:
    color = "\033[1;97m"
    print(f"\n{color}{'=' * WIDTH}{RESET}")
    print(f"{color}  PARALLEL EVALUATION -- stage 1 of 2{RESET}")
    print(f"{color}  Each specialist sees ONLY the user query -- zero cross-agent influence{RESET}")
    print(f"{color}  Events below are INTERLEAVED (async completion order){RESET}")
    print(f"{color}{'=' * WIDTH}{RESET}\n")


def print_parallel_agent_active(agent: str) -> None:
    color = AGENT_COLORS.get(agent, BOLD)
    print(f"\n{color}  -- {agent_label(agent)}{RESET}")


def print_parallel_complete(specialist_texts: dict) -> None:
    color = "\033[1;97m"
    total = len(SPECIALISTS)
    print(f"\n{color}{'=' * WIDTH}{RESET}")
    print(f"{color}  PARALLEL EVALUATION COMPLETE  --  {len(specialist_texts)}/{total} specialists{RESET}")
    for s in SPECIALISTS:
        title, loc = AGENT_META[s.name]
        check = "OK" if s.name in specialist_texts else "MISSING"
        ac = AGENT_COLORS.get(s.name, BOLD)
        print(f"  {ac}  [{check}] {title:<22} ({loc}){RESET}")
    print(f"{color}{'=' * WIDTH}{RESET}")
