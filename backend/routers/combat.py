"""FastAPI router for /api/combat/* endpoints."""
from __future__ import annotations
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.schemas.combat_end import CombatEndPayload
from backend.schemas.combat_session import CombatSession, SessionStatus
from backend.services.combat_engine import combat_engine
from backend.services.mock_gemini import trigger_combat_encounter
from backend.state.store import session_store

logger = logging.getLogger(__name__)
router = APIRouter()


class TriggerCombatRequest(BaseModel):
    player_ids: Optional[list[str]] = None
    enemy_ids: Optional[list[str]] = None
    scene_index: int = 0


class TriggerCombatResponse(BaseModel):
    combat_id: str
    status: str
    initiative_order: list[str]
    message: str


class SessionSummary(BaseModel):
    combat_id: str
    status: SessionStatus
    current_round: int
    current_combatant_id: Optional[str]
    combatant_count: int


@router.post("/trigger", response_model=TriggerCombatResponse)
async def trigger_combat(
    request: TriggerCombatRequest = TriggerCombatRequest(),
) -> TriggerCombatResponse:
    """Simulate Gemini DM triggering a combat encounter.
    In Phase 4, this receives a real Gemini function_call webhook.
    """
    payload = await trigger_combat_encounter(
        player_ids=request.player_ids,
        enemy_ids=request.enemy_ids,
        scene_index=request.scene_index,
    )
    session = CombatSession(
        combat_id=payload.combat_id,
        start_payload=payload,
        status=SessionStatus.pending,
    )
    initiative_results = combat_engine.roll_initiative_order(session)
    session.status = SessionStatus.active
    await session_store.create(session)
    logger.info("Combat triggered: %s", session.combat_id)
    return TriggerCombatResponse(
        combat_id=session.combat_id,
        status=session.status.value,
        initiative_order=session.initiative_order,
        message=(
            f"Combat started in '{payload.scene.terrain.value}'. "
            f"{len(session.initiative_order)} combatants ready. "
            f"First turn: {initiative_results[0].name}"
        ),
    )


@router.get("/list/active")
async def list_active_sessions() -> dict:
    """Dev utility — list all active combat sessions."""
    sessions = await session_store.list_active()
    return {
        "active_count": len(sessions),
        "sessions": [{"combat_id": s.combat_id, "round": s.current_round} for s in sessions],
    }


@router.get("/{combat_id}", response_model=SessionSummary)
async def get_session(combat_id: str) -> SessionSummary:
    """Fetch the current state of a combat session."""
    session = await session_store.get(combat_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{combat_id}' not found")
    return SessionSummary(
        combat_id=session.combat_id,
        status=session.status,
        current_round=session.current_round,
        current_combatant_id=session.current_combatant_id,
        combatant_count=len(session.start_payload.combatants),
    )


@router.post("/result")
async def submit_combat_result(payload: CombatEndPayload) -> dict:
    """Receive combat outcome from client.
    In Phase 4, forwards to Gemini as function_response to resume narration.
    """
    session = await session_store.get(payload.combat_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{payload.combat_id}' not found")
    if session.status != SessionStatus.active:
        raise HTTPException(
            status_code=409,
            detail=f"Session is '{session.status.value}', expected 'active'",
        )
    session.end_payload = payload
    session.status = SessionStatus.completed
    await session_store.update(session)
    logger.info("Combat result: id=%s outcome=%s rounds=%d",
                payload.combat_id, payload.outcome.value, payload.duration_rounds)
    return {
        "status": "accepted",
        "combat_id": payload.combat_id,
        "outcome": payload.outcome.value,
        "dm_continuation": "[Phase 4: Gemini will continue the story here]",
    }
