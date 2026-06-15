"""Pydantic models for the combat_end payload.

Data contract: Combat Simulator -> Gemini DM.
Client POSTs this to /api/combat/result after combat ends.
"""
from __future__ import annotations
from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, Field, model_validator


class CombatOutcome(str, Enum):
    victory = "victory"
    defeat = "defeat"
    retreat = "retreat"
    enemy_fled = "enemy_fled"
    draw = "draw"


class DeathType(str, Enum):
    killed = "killed"
    downed = "downed"
    fled = "fled"


class NarrativeTag(str, Enum):
    """Semantic tags that help Gemini write a fitting narrative continuation."""
    solid_hit = "solid_hit"
    glancing_blow = "glancing_blow"
    killing_blow = "killing_blow"
    near_death = "near_death"
    turning_point = "turning_point"
    critical_hit = "critical_hit"
    critical_miss = "critical_miss"
    spell_cast = "spell_cast"
    condition_applied = "condition_applied"
    legendary_action = "legendary_action"


class Survivor(BaseModel):
    id: str
    name: str
    final_hp: Annotated[int, Field(ge=0)]
    max_hp: Annotated[int, Field(ge=1)]
    conditions_remaining: list[str] = Field(default_factory=list)

    @property
    def hp_percentage(self) -> float:
        return round(self.final_hp / self.max_hp * 100, 1)


class Defeated(BaseModel):
    id: str
    name: str
    death_type: DeathType
    killed_by: Optional[str] = None
    killing_blow: Optional[str] = None


class SpellSlotsSpent(BaseModel):
    level_1: Annotated[int, Field(ge=0)] = 0
    level_2: Annotated[int, Field(ge=0)] = 0
    level_3: Annotated[int, Field(ge=0)] = 0
    level_4: Annotated[int, Field(ge=0)] = 0
    level_5: Annotated[int, Field(ge=0)] = 0
    level_6: Annotated[int, Field(ge=0)] = 0
    level_7: Annotated[int, Field(ge=0)] = 0
    level_8: Annotated[int, Field(ge=0)] = 0
    level_9: Annotated[int, Field(ge=0)] = 0


class ResourcesSpent(BaseModel):
    combatant_id: str
    spell_slots: SpellSlotsSpent = SpellSlotsSpent()
    named_resources_used: list[str] = Field(default_factory=list)
    hit_dice_spent: Annotated[int, Field(ge=0)] = 0


class AttackRoll(BaseModel):
    total: Annotated[int, Field(ge=1, le=30)]
    natural: Annotated[int, Field(ge=1, le=20)]
    is_crit: bool = False
    is_crit_fail: bool = False

    @model_validator(mode="after")
    def crit_and_crit_fail_exclusive(self) -> "AttackRoll":
        if self.is_crit and self.is_crit_fail:
            raise ValueError("A roll cannot be both a critical hit and a critical fail")
        return self


class EventLogEntry(BaseModel):
    """A single meaningful combat event. Gemini reads this for narrative context."""
    round: Annotated[int, Field(ge=1)]
    turn: str
    action_id: str
    target_id: Optional[str] = None
    attack_roll: Optional[AttackRoll] = None
    damage_dealt: Optional[Annotated[int, Field(ge=0)]] = None
    healing_done: Optional[Annotated[int, Field(ge=0)]] = None
    condition_applied: Optional[str] = None
    narrative_tag: NarrativeTag
    detail: Optional[str] = Field(default=None, max_length=200)


class LootItem(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    quantity: Annotated[int, Field(ge=1)] = 1


class CombatEndPayload(BaseModel):
    """Root model: Simulator -> Gemini DM data contract."""
    combat_id: str
    duration_rounds: Annotated[int, Field(ge=1)]
    outcome: CombatOutcome
    survivors: list[Survivor] = Field(default_factory=list)
    defeated: list[Defeated] = Field(default_factory=list)
    resources_spent: list[ResourcesSpent] = Field(default_factory=list)
    event_log: list[EventLogEntry] = Field(default_factory=list)
    loot_acquired: list[LootItem] = Field(default_factory=list)
    dm_prompt_injection: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def victory_requires_survivors(self) -> "CombatEndPayload":
        if self.outcome == CombatOutcome.victory and not self.survivors:
            raise ValueError("A victory must have at least one survivor")
        return self
