import logging

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.graph.state import AgentState
from src.graph.utils.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an intelligent task management assistant for an organization.
Your job is to answer questions about tasks and personnel accurately.

Rules:
1. Always use the provided tools to fetch data — never guess or fabricate numbers.
2. If a question is outside the domain of tasks and personnel (e.g. weather, cooking,
   general knowledge, coding help), politely decline and explain you can only help
   with organizational tasks and personnel data.
3. If a question is ambiguous (e.g. 'show tasks' without specifying whose or which status),
   ask ONE clarifying question before calling any tool.
4. Keep answers concise and accurate.
5. Never produce made-up information.

Respond in the same language the user writes in."""

_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def make_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.1,
        # reasoning_effort="minimal",
        openai_api_key=settings.OPENAI_API_KEY,
        openai_proxy=settings.OPENAI_PROXY,
    ).bind_tools(ALL_TOOLS)


async def llm_node(state: AgentState, llm: ChatOpenAI) -> dict:
    messages = [SystemMessage(content=_SYSTEM_PROMPT)] + list(state.messages)
    response: AIMessage = await llm.ainvoke(messages)
    logger.debug("LLM response tool_calls=%s", bool(response.tool_calls))
    logger.info(
        "llm_node: tool_calls=%r content_preview=%r",
        [c["name"] for c in response.tool_calls],
        str(response.content)[:120],
    )
    return {"messages": [response]}


async def tool_node(state: AgentState) -> dict:
    last: AIMessage = state.messages[-1]
    tool_messages: list[ToolMessage] = []

    for call in last.tool_calls:
        name = call["name"]
        args = call["args"]
        logger.info("Tool call: %s(%s)", name, args)
        try:
            result = await _TOOL_MAP[name].ainvoke(args)
        except KeyError:
            result = f"Error: tool '{name}' does not exist."
        except Exception as e:
            logger.exception("Tool %s failed", name)
            result = f"Error executing tool: {e}"

        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"], name=name))

    return {"messages": tool_messages}
