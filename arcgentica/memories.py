from dataclasses import dataclass, field
from datetime import datetime

from agentica import Agent, spawn

from arcgentica.models import SUBAGENT_MODEL


@dataclass(slots=True, frozen=True)
class Memory:
    """
    A vital piece of information that should be remembered across all future agents.

    summary: a short, high-level description of the information.
    details: a detailed description of the information.
    """

    summary: str
    details: str
    timestamp: datetime = field(default_factory=datetime.now)


class MemoryQueryError(Exception):
    """Raised when a memory query is not possible to answer with the given memories or in the desired format."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Memories:
    """
    A database of shared memories/information.
    Use this to store and retrieve crucial insights, observations, and knowledge.

    Keep entries factual. In the details, clearly separate what is confirmed from
    what is hypothesised, e.g. "CONFIRMED: ... HYPOTHESIS: ...". Other agents
    trust this database -- unverified guesses written as facts will mislead them.
    """

    stack: list[Memory]
    _memory_agent: Agent

    def __init__(self) -> None:
        self.stack = []
        self._memory_agent = spawn(
            model=SUBAGENT_MODEL,
            premise="You are a memory agent. You are responsible for storing and retrieving crucial insights, observations, and knowledge.",
            scope={"memories": self, "MemoryQueryError": MemoryQueryError},
        )

    def add(self, summary: str, details: str) -> None:
        """Append an insight."""
        self.stack.append(Memory(summary, details))

    def get(self, i: int) -> Memory:
        """Retrieve an insight by index. Negative indices are supported."""
        return self.stack[i]

    def evict(self, i: int | None = None) -> None:
        """Remove an insight by index. If no index is provided, pop the last insight."""
        self.stack.pop(i)

    def query[T](self, return_type: type[T], query: str) -> T:
        """
        Natural language query information from the memories.

        Use `return_type` and `query` to structure how and what information to retrieve.

        Example:
            memories.query(list[int], "What what triggers X to happen? Gice me a list of indices for the corresponding memory entries.")
            memories.query(str, "What is the premise of the level X?")
            memories.query(Memory, "What happens when I take action X?")
            memories.query(list[Memory], "Give me the last 3 memories pertaining to level X.")
        """
        return self._memory_agent.call(
            return_type,
            f"Your task is to retrieve information from the memories based on the query.\n"
            f"You must be diligent and inspect any new memories that may have been added since the last query.\n"
            f"You may raise an exception if the query is not possible to answer with the given memories, should they be insufficient or too unclear.\n"
            f"You should not make up information, you must only return in the desired format if the format is appropriate for the query, otherwise raise an exception.\n"
            f"You have been given the following query: {query}",
            stack=self.stack,
        )

    def __repr__(self) -> str:
        return f"Memories(<{len(self.stack)} memories>)"
