"""Lab 6.4 - Deadlocks (and livelocks) in multi-agent systems.

No model needed: these are coordination bugs, the same ones databases and
operating systems have. Agents make them easy to create because each agent
politely waits for the other.

  A. RESOURCE DEADLOCK  two agents each hold one lock and wait for the other's
  B. WAIT-FOR CYCLE     A waits for B's output, B waits for A's
  C. LIVELOCK           agents keep handing work back and forth forever

Run:  python modules/06-memory-multi-agent/labs/04_deadlocks.py
"""

import threading
import time

# ---------------------------------------------------------------- A. resource deadlock
print("A. RESOURCE DEADLOCK")
config_file, deploy_slot = threading.Lock(), threading.Lock()


def agent(name: str, first: threading.Lock, second: threading.Lock, log: list, timeout: float):
    with first:
        time.sleep(0.05)  # both agents now hold their first lock
        if second.acquire(timeout=timeout):  # without a timeout this waits forever
            second.release()
            log.append(f"{name}: done")
        else:
            log.append(f"{name}: gave up waiting, released its lock, will retry later")


def run_pair(order_a, order_b, timeout=0.3) -> list:
    log: list = []
    threads = [threading.Thread(target=agent, args=("fixer   ", *order_a, log, timeout)),
               threading.Thread(target=agent, args=("deployer", *order_b, log, timeout))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return log

# Opposite lock order -> classic deadlock, broken only by the timeout.
print("  opposite order:", run_pair((config_file, deploy_slot), (deploy_slot, config_file)))
# FIX 1: everyone acquires resources in the SAME global order.
print("  same order:    ", run_pair((config_file, deploy_slot), (config_file, deploy_slot)))

# ---------------------------------------------------------------- B. wait-for cycle
print("\nB. WAIT-FOR CYCLE")
waiting_for = {"planner": "researcher", "researcher": "reviewer", "reviewer": "planner"}


def find_cycle(graph: dict) -> list | None:
    """Follow who-waits-for-whom. Returning to a visited agent means deadlock."""
    for start in graph:
        path, node = [start], graph.get(start)
        while node is not None:
            if node in path:
                return path[path.index(node):] + [node]
            path.append(node)
            node = graph.get(node)
    return None

print("  cycle detected:", " -> ".join(find_cycle(waiting_for)))
print("  after orchestrator cancels reviewer's wait:", find_cycle({**waiting_for, "reviewer": None}))
# FIX 2: a supervisor (or the orchestrator) owns the wait-for graph and breaks cycles.
# FIX 3: make it impossible - a tree: only the orchestrator delegates, specialists
#        never call each other or call back up.

# ---------------------------------------------------------------- C. livelock
print("\nC. LIVELOCK (writer <-> critic)")


def critic(draft_number: int) -> str:
    return "approve" if draft_number >= 100 else "revise"  # a critic that is never satisfied


def write_with_review(max_rounds: int) -> str:
    for round_number in range(1, max_rounds + 1):
        if critic(round_number) == "approve":
            return f"approved in round {round_number}"
    return f"stopped after {max_rounds} rounds: escalate to a human with the best draft so far"

print(" ", write_with_review(max_rounds=3))
# FIX 4: bound every loop between agents (max rounds, max handoffs, deadline, budget)
#        and define what happens when the bound is hit.

print("""
The checklist for any multi-agent design:
  [ ] Every wait has a timeout.                     (A, B)
  [ ] Shared resources are acquired in one global order, or owned by ONE agent.  (A)
  [ ] Delegation is a tree, not a graph; no agent waits on its caller.           (B)
  [ ] Every agent-to-agent loop has a round limit and an escalation path.        (C)
  [ ] One component (the orchestrator) can see all in-flight work and cancel it.
  [ ] Handoff counts and deadlines travel WITH the task, so no agent resets them.""")

# Try it:
# 1. Remove the timeout in A (use second.acquire()). Watch the program hang;
#    that is what a deadlocked agent system looks like in production: silence.
# 2. Model B with real threads and queues: each agent blocks on queue.get().
# 3. Two "helpful" agents each say "after you". Write that livelock, then fix it.
