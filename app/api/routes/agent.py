"""Agent Chat REST API endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.agent import AgentService
from app.agent.schemas import AgentRequest, AgentResponse
from app.core.config import get_settings
from app.core.errors import AppException
from app.core.logging import logger
from app.core.security import UserPrincipal, get_current_user

router = APIRouter(prefix="/agent", tags=["AI Agent"])
settings = get_settings()

# Cached or lazily initialized agent service
_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest,
    service: AgentService = Depends(get_agent_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Interact with the business assistant using natural language.

    The agent dynamically selects and invokes MCP tools, obeys guardrails,
    and returns a structured execution trace. Write operations require human confirmation.
    """
    try:
        response = await service.run(request)
        return response
    except ConnectionError as exc:
        logger.error(f"LLM backend unreachable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable. Standard API functionality remains available.",
        )
    except AppException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected chat endpoint error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent workflow: {str(exc)}",
        )
