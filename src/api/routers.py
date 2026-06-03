from langchain_core.messages import HumanMessage, AIMessage
import uuid
from fastapi import APIRouter, Request, HTTPException, status
from langgraph.graph.state import CompiledStateGraph
from openai import APITimeoutError, RateLimitError, APIConnectionError

from src.schema.main_schema import RecieveSchema, ResponseSchema

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ResponseSchema)
async def chat_endpoint(req: RecieveSchema, request: Request) -> ResponseSchema:
    graph: CompiledStateGraph = request.app.state.graph  # injected by lifespan
    conv_id = req.conversation_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(req.message)]},
            config=config,
        )
    except APITimeoutError as e:
        logger.warning("conv=%s LLM timeout: %s", conv_id, e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM request timed out. Please try again.",
        )
    except RateLimitError as e:
        logger.warning("conv=%s LLM rate limit: %s", conv_id, e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached.",
        )
    except APIConnectionError as e:
        logger.error("conv=%s LLM connection error: %s", conv_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach LLM service.",
        )
    except Exception:
        logger.exception("conv=%s unexpected error", conv_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
    answer = next(
        m.content
        for m in reversed(result["messages"])
        if isinstance(m, AIMessage) and not m.tool_calls
    )
    return ResponseSchema(conversation_id=conv_id, answer=answer)
