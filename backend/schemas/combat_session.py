"""Internal session model — combines start payload with runtime state."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from backend.schemas.combat_start import CombatStartPayload
from backend.schemas.combat_end import CombatEndPayload


class SessionStatus(str, Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    expired = "expired"


class CombatSession(BaseModel):
    """Full runtime state of a single combat encounter."""
    combat_id: str
    status: SessionStatus = SessionStatus.pending
    start_payload: CombatStartPayload
    end_payload: Optional[CombatEndPayload] = None
    current_round: int = Field(default=1, ge=1)
    initiative_order: list[str] = Field(default_factory=list)
    current_turn_index: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def advance_turn(self) -> str:
        """Move to the next combatant. Returns current combatant ID."""
        self.current_turn_index = (self.current_turn_index + 1) % len(self.initiative_order)
        if self.current_turn_index == 0:
            self.current_round += 1
        self.updated_at = datetime.now(timezone.utc)
        return self.initiative_order[self.current_turn_index]

    @property
    def current_combatant_id(self) -> Optional[str]:
        if not self.initiative_order:
            return None
        return self.initiative_order[self.current_turn_index]
