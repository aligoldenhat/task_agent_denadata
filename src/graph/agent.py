from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncGenerator, Literal

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.graph.nodes import llm_node, make_llm, tool_node
from src.graph.state import AgentState


def _route(state: AgentState) -> Literal["tool_node", "__end__"]:
    last = state.messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tool_node"
    return "__end__"


def _compile(checkpointer: AsyncSqliteSaver) -> CompiledStateGraph:
    llm = make_llm()
    builder = StateGraph(AgentState)

    builder.add_node("llm_node", partial(llm_node, llm=llm))
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "llm_node")
    builder.add_conditional_edges("llm_node", _route)
    builder.add_edge("tool_node", "llm_node")

    return builder.compile(checkpointer=checkpointer)


@asynccontextmanager
async def lifespan_graph(db_path: str) -> AsyncGenerator:
    """
    Open one aiosqlite connection for the entire app lifetime.
    Yields the compiled graph — store it wherever you need it.

    Usage in FastAPI lifespan:
        async with lifespan_graph("memory.db") as graph:
            app.state.graph = graph
            yield
    """
    async with aiosqlite.connect(db_path) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        yield _compile(checkpointer)
