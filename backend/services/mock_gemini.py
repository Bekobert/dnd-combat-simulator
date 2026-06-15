"""Mock Gemini DM service — simulates Gemini function calling output.

In Phase 4 this is replaced with real Gemini API calls via httpx.
The interface (trigger_combat_encounter) stays identical — no caller changes.

Gemini function_calling flow (Phase 4 reference):
  1. Narrative arrives in Gemini conversation.
  2. Gemini decides combat should start.
  3. Gemini emits a function_call with name='trigger_combat' and JSON args
     matching CombatStartPayload.
  4. Backend validates with Pydantic, stores session.
  5. Backend sends function_response back to Gemini to continue narration.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from ulid import ULID
from backend.schemas.combat_start import CombatStartPayload

logger = logging.getLogger(__name__)

_PLAYER_TEMPLATES: list[dict] = [
    {
        "id": "player_aldric", "name": "Aldric", "type": "player",
        "class": "Fighter", "level": 5, "sprite": "fighter_m_01",
        "stats": {
            "hp": {"current": 42, "max": 52}, "ac": 17, "speed": 30,
            "ability_scores": {"str": 18, "dex": 12, "con": 16, "int": 8, "wis": 10, "cha": 10},
            "saving_throws": {"str": 7, "con": 6},
        },
        "resources": {"named": {
            "second_wind": {"uses_remaining": 1, "max": 1},
            "action_surge": {"uses_remaining": 1, "max": 1},
        }},
        "abilities": [
            {"id": "longsword_attack", "name": "Longsword", "action_cost": "action",
             "range_ft": 5, "damage_dice": "1d8+4", "damage_type": "slashing", "attack_bonus": 7},
            {"id": "second_wind", "name": "Second Wind", "action_cost": "bonus_action",
             "range_ft": 0, "description": "Regain 1d10+5 HP"},
            {"id": "action_surge", "name": "Action Surge", "action_cost": "free",
             "range_ft": 0, "description": "Take one additional action this turn"},
        ],
    },
    {
        "id": "player_seraphina", "name": "Seraphina", "type": "player",
        "class": "Wizard", "level": 5, "sprite": "wizard_f_01",
        "stats": {
            "hp": {"current": 28, "max": 28}, "ac": 13, "speed": 30,
            "ability_scores": {"str": 8, "dex": 14, "con": 12, "int": 18, "wis": 12, "cha": 10},
        },
        "resources": {"spell_slots": {"level_1": 4, "level_2": 3, "level_3": 2}},
        "abilities": [
            {"id": "fireball", "name": "Fireball", "action_cost": "action",
             "range_ft": 150, "damage_dice": "8d6", "damage_type": "fire",
             "spell_level": 3, "save_dc": 15},
            {"id": "magic_missile", "name": "Magic Missile", "action_cost": "action",
             "range_ft": 120, "damage_dice": "3d4", "damage_type": "force", "spell_level": 1},
        ],
    },
]

_ENEMY_TEMPLATES: list[dict] = [
    {
        "id": "enemy_goblin_boss", "name": "Goblin Sefi Krax", "type": "enemy",
        "cr": 1.0, "sprite": "goblin_boss_01", "ai_behavior": "aggressive",
        "loot_table": "goblin_boss_loot",
        "stats": {"hp": {"current": 21, "max": 21}, "ac": 15, "speed": 30,
                  "ability_scores": {"str": 8, "dex": 14, "con": 10, "int": 8, "wis": 8, "cha": 8}},
        "abilities": [
            {"id": "scimitar", "name": "Scimitar", "action_cost": "action",
             "range_ft": 5, "damage_dice": "1d6+2", "damage_type": "slashing", "attack_bonus": 4},
            {"id": "nimble_escape", "name": "Nimble Escape", "action_cost": "bonus_action",
             "range_ft": 0, "description": "Disengage or Hide as a bonus action"},
        ],
    },
    {
        "id": "enemy_orc_warrior", "name": "Orc Warrior", "type": "enemy",
        "cr": 0.5, "sprite": "orc_warrior_01", "ai_behavior": "berserker",
        "stats": {"hp": {"current": 15, "max": 15}, "ac": 13, "speed": 30},
        "abilities": [
            {"id": "greataxe", "name": "Greataxe", "action_cost": "action",
             "range_ft": 5, "damage_dice": "1d12+3", "damage_type": "slashing", "attack_bonus": 5},
        ],
    },
]

_SCENE_TEMPLATES: list[dict] = [
    {"description": "A narrow dungeon corridor before the goblin leader's wooden throne",
     "terrain": "dungeon_corridor", "grid": {"width": 12, "height": 8, "tile_size": 64}},
    {"description": "The main hall of an abandoned tavern, moonlight streaming through the windows",
     "terrain": "tavern", "grid": {"width": 16, "height": 12, "tile_size": 64}},
]


async def trigger_combat_encounter(
    player_ids: Optional[list[str]] = None,
    enemy_ids: Optional[list[str]] = None,
    scene_index: int = 0,
    simulate_latency: bool = True,
) -> CombatStartPayload:
    """Simulate a Gemini function_call that triggers a combat encounter.

    Args:
        player_ids: Which player templates to include. Defaults to Aldric (Fighter).
        enemy_ids: Which enemy templates to include. Defaults to Goblin Boss.
        scene_index: Which scene template to use.
        simulate_latency: Adds ~50ms sleep to simulate real API call.

    Returns:
        Validated CombatStartPayload ready to be stored in the session store.
    """
    if simulate_latency:
        await asyncio.sleep(0.05)

    player_pool = {t["id"]: t for t in _PLAYER_TEMPLATES}
    enemy_pool = {t["id"]: t for t in _ENEMY_TEMPLATES}

    selected_players = (
        [player_pool[pid] for pid in player_ids if pid in player_pool]
        if player_ids else [_PLAYER_TEMPLATES[0]]
    )
    selected_enemies = (
        [enemy_pool[eid] for eid in enemy_ids if eid in enemy_pool]
        if enemy_ids else [_ENEMY_TEMPLATES[0]]
    )

    scene_data = _SCENE_TEMPLATES[scene_index % len(_SCENE_TEMPLATES)]
    combat_id = str(ULID())
    grid_width = scene_data["grid"]["width"]
    grid_height = scene_data["grid"]["height"]
    mid_y = grid_height // 2

    combatants_raw = []
    for i, p in enumerate(selected_players):
        raw = dict(p)
        raw["position"] = {"x": 2, "y": mid_y - i}
        combatants_raw.append(raw)
    for i, e in enumerate(selected_enemies):
        raw = dict(e)
        raw["position"] = {"x": grid_width - 3, "y": mid_y - i}
        combatants_raw.append(raw)

    payload_dict = {
        "combat_id": combat_id,
        "scene": scene_data,
        "combatants": combatants_raw,
        "narrative_context": {
            "preceding_summary": (
                "The party ventured deep into the dungeon. As they pushed open the rusted "
                "iron door, they were met by the cold gaze of Goblin Chief Krax upon his "
                "wooden throne. 'Guests,' Krax sneered, drawing his rusted blade."
            ),
            "dm_notes": (
                "Krax will attempt to flee if HP drops below 30%. "
                "If the player shows mercy, turn this into a future quest hook."
            ),
        },
        "initiative_order": [],
    }

    logger.info("Mock Gemini triggered combat: id=%s", combat_id)
    return CombatStartPayload.model_validate(payload_dict)
