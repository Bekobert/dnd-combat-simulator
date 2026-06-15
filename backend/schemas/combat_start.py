"""Pydantic models for the combat_start payload.

Data contract: Gemini DM -> Combat Simulator.
Gemini produces this via function calling; backend validates and stores it.

Design:
- Every numeric field has explicit D&D 5e bounds.
- Optional fields use None — never empty strings or magic numbers.
"""
from __future__ import annotations
from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CombatantType(str, Enum):
    player = "player"
    enemy = "enemy"
    ally = "ally"
    neutral = "neutral"


class TerrainType(str, Enum):
    dungeon_corridor = "dungeon_corridor"
    open_field = "open_field"
    forest = "forest"
    cave = "cave"
    urban_street = "urban_street"
    tavern = "tavern"
    castle_hall = "castle_hall"


class ActionCost(str, Enum):
    action = "action"
    bonus_action = "bonus_action"
    reaction = "reaction"
    free = "free"
    legendary = "legendary"


class DamageType(str, Enum):
    slashing = "slashing"
    piercing = "piercing"
    bludgeoning = "bludgeoning"
    fire = "fire"
    cold = "cold"
    lightning = "lightning"
    acid = "acid"
    poison = "poison"
    psychic = "psychic"
    necrotic = "necrotic"
    radiant = "radiant"
    thunder = "thunder"
    force = "force"


class Condition(str, Enum):
    blinded = "blinded"
    charmed = "charmed"
    frightened = "frightened"
    grappled = "grappled"
    incapacitated = "incapacitated"
    invisible = "invisible"
    paralyzed = "paralyzed"
    poisoned = "poisoned"
    prone = "prone"
    stunned = "stunned"
    unconscious = "unconscious"
    exhaustion_1 = "exhaustion_1"
    exhaustion_2 = "exhaustion_2"
    exhaustion_3 = "exhaustion_3"


class AiBehavior(str, Enum):
    aggressive = "aggressive"
    defensive = "defensive"
    cowardly = "cowardly"
    tactical = "tactical"
    berserker = "berserker"


class GridPosition(BaseModel):
    x: Annotated[int, Field(ge=0)]
    y: Annotated[int, Field(ge=0)]


class GridConfig(BaseModel):
    width: Annotated[int, Field(ge=4, le=32)]
    height: Annotated[int, Field(ge=4, le=24)]
    tile_size: Annotated[int, Field(ge=32, le=128)] = 64


class AbilityScores(BaseModel):
    """Six core D&D ability scores. Range 1-30."""
    str_: Annotated[int, Field(ge=1, le=30, alias="str")] = 10
    dex: Annotated[int, Field(ge=1, le=30)] = 10
    con: Annotated[int, Field(ge=1, le=30)] = 10
    int_: Annotated[int, Field(ge=1, le=30, alias="int")] = 10
    wis: Annotated[int, Field(ge=1, le=30)] = 10
    cha: Annotated[int, Field(ge=1, le=30)] = 10
    model_config = {"populate_by_name": True}


class SavingThrows(BaseModel):
    str_: Optional[Annotated[int, Field(ge=-5, le=20, alias="str")]] = None
    dex: Optional[Annotated[int, Field(ge=-5, le=20)]] = None
    con: Optional[Annotated[int, Field(ge=-5, le=20)]] = None
    int_: Optional[Annotated[int, Field(ge=-5, le=20, alias="int")]] = None
    wis: Optional[Annotated[int, Field(ge=-5, le=20)]] = None
    cha: Optional[Annotated[int, Field(ge=-5, le=20)]] = None
    model_config = {"populate_by_name": True}


class HitPoints(BaseModel):
    """Current HP clamped to [0, max] by validator."""
    current: Annotated[int, Field(ge=0)]
    max: Annotated[int, Field(ge=1, le=1000)]

    @model_validator(mode="after")
    def current_cannot_exceed_max(self) -> "HitPoints":
        if self.current > self.max:
            raise ValueError(f"current HP ({self.current}) cannot exceed max HP ({self.max})")
        return self


class ResourceUse(BaseModel):
    uses_remaining: Annotated[int, Field(ge=0)]
    max: Annotated[int, Field(ge=1)]


class SpellSlots(BaseModel):
    level_1: Annotated[int, Field(ge=0, le=4)] = 0
    level_2: Annotated[int, Field(ge=0, le=3)] = 0
    level_3: Annotated[int, Field(ge=0, le=3)] = 0
    level_4: Annotated[int, Field(ge=0, le=3)] = 0
    level_5: Annotated[int, Field(ge=0, le=3)] = 0
    level_6: Annotated[int, Field(ge=0, le=2)] = 0
    level_7: Annotated[int, Field(ge=0, le=2)] = 0
    level_8: Annotated[int, Field(ge=0, le=1)] = 0
    level_9: Annotated[int, Field(ge=0, le=1)] = 0


class Mana(BaseModel):
    current: Annotated[int, Field(ge=0)]
    max: Annotated[int, Field(ge=0)]


class CombatantStats(BaseModel):
    hp: HitPoints
    ac: Annotated[int, Field(ge=1, le=30)]
    speed: Annotated[int, Field(ge=0, le=120)] = 30
    ability_scores: AbilityScores = AbilityScores()
    saving_throws: SavingThrows = SavingThrows()


class CombatantResources(BaseModel):
    action: bool = True
    bonus_action: bool = True
    reaction: bool = True
    spell_slots: SpellSlots = SpellSlots()
    mana: Optional[Mana] = None
    named: dict[str, ResourceUse] = Field(default_factory=dict)


class Ability(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=60)
    action_cost: ActionCost
    range_ft: Annotated[int, Field(ge=0, le=600)] = 5
    damage_dice: Optional[str] = Field(default=None, pattern=r"^\d+d\d+(\+\d+)?$")
    damage_type: Optional[DamageType] = None
    attack_bonus: Optional[Annotated[int, Field(ge=-5, le=20)]] = None
    spell_level: Optional[Annotated[int, Field(ge=0, le=9)]] = None
    save_dc: Optional[Annotated[int, Field(ge=1, le=30)]] = None
    description: Optional[str] = Field(default=None, max_length=300)

    @field_validator("damage_dice")
    @classmethod
    def validate_dice_notation(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        parts = v.replace("+", "d").split("d")
        num_dice, die_size = int(parts[0]), int(parts[1])
        if num_dice > 20:
            raise ValueError("More than 20 dice is not valid in D&D 5e")
        if die_size not in (4, 6, 8, 10, 12, 20, 100):
            raise ValueError(f"Invalid die size: d{die_size}")
        return v


class Scene(BaseModel):
    description: str = Field(max_length=1000)
    terrain: TerrainType
    grid: GridConfig
    ambient_notes: Optional[str] = Field(default=None, max_length=300)


class NarrativeContext(BaseModel):
    preceding_summary: str = Field(max_length=2000)
    dm_notes: Optional[str] = Field(default=None, max_length=1000)


class Combatant(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    type: CombatantType
    position: GridPosition
    stats: CombatantStats
    resources: CombatantResources = CombatantResources()
    conditions: list[Condition] = Field(default_factory=list)
    abilities: list[Ability] = Field(default_factory=list)
    sprite: Optional[str] = None
    cr: Optional[Annotated[float, Field(ge=0, le=30)]] = None
    ai_behavior: Optional[AiBehavior] = None
    loot_table: Optional[str] = None
    class_: Optional[str] = Field(default=None, alias="class", max_length=40)
    level: Optional[Annotated[int, Field(ge=1, le=20)]] = None
    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def enemy_should_have_ai(self) -> "Combatant":
        if self.type == CombatantType.enemy and self.ai_behavior is None:
            self.ai_behavior = AiBehavior.aggressive
        return self


class CombatStartPayload(BaseModel):
    """Root model: LLM -> Simulator data contract."""
    combat_id: str
    scene: Scene
    combatants: list[Combatant] = Field(min_length=2)
    narrative_context: NarrativeContext
    initiative_order: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_initiative_ids(self) -> "CombatStartPayload":
        if not self.initiative_order:
            return self
        combatant_ids = {c.id for c in self.combatants}
        unknown = set(self.initiative_order) - combatant_ids
        if unknown:
            raise ValueError(f"initiative_order references unknown IDs: {unknown}")
        return self

    @model_validator(mode="after")
    def at_least_one_player_and_enemy(self) -> "CombatStartPayload":
        types = {c.type for c in self.combatants}
        if CombatantType.player not in types:
            raise ValueError("Combat must include at least one player combatant")
        if CombatantType.enemy not in types:
            raise ValueError("Combat must include at least one enemy combatant")
        return self
