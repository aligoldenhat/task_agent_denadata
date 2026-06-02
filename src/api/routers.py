from langchain_core.messages import HumanMessage, AIMessage
import uuid
from fastapi import APIRouter, Request
from langgraph.graph.state import CompiledStateGraph

from src.schema.main_schema import RecieveSchema, ResponseSchema

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ResponseSchema)
async def chat_endpoint(req: RecieveSchema, request: Request) -> ResponseSchema:
    graph: CompiledStateGraph = request.app.state.graph  # injected by lifespan
    conv_id = req.conversation_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}

    result = await graph.ainvoke(
        {"messages": [HumanMessage(req.message)]},
        config=config,
    )
    answer = next(
        m.content
        for m in reversed(result["messages"])
        if isinstance(m, AIMessage) and not m.tool_calls
    )
    return ResponseSchema(conversation_id=conv_id, answer=answer)
