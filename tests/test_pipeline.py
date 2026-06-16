"""End-to-end pipeline tests for Phase 0 + Phase 1.

Flow tested:
    mock Gemini -> Pydantic validation -> state store -> combat engine -> HTTP endpoints

Run with:
    python -m pytest tests/test_pipeline.py -v
    python -m pytest tests/test_pipeline.py -v --log-cli-level=INFO
"""
from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.schemas.combat_start import CombatStartPayload, HitPoints
from backend.schemas.combat_end import AttackRoll, CombatEndPayload, CombatOutcome
from backend.schemas.combat_session import CombatSession, SessionStatus
from backend.services.mock_gemini import trigger_combat_encounter
from backend.services.combat_engine import CombatEngine, ability_modifier, parse_and_roll_dice
from backend.state.store import InMemorySessionStore


@pytest.fixture
def engine() -> CombatEngine:
    return CombatEngine()

@pytest.fixture
def store() -> InMemorySessionStore:
    return InMemorySessionStore()

@pytest.fixture
async def session(store: InMemorySessionStore, engine: CombatEngine) -> CombatSession:
    payload = await trigger_combat_encounter(simulate_latency=False)
    s = CombatSession(combat_id=payload.combat_id, start_payload=payload)
    engine.roll_initiative_order(s)
    s.status = SessionStatus.active
    await store.create(s)
    return s


class TestSchemas:
    def test_hp_cannot_exceed_max(self):
        with pytest.raises(ValueError, match="cannot exceed max"):
            HitPoints(current=100, max=50)

    def test_hp_cannot_be_negative(self):
        with pytest.raises(ValueError):
            HitPoints(current=-1, max=50)

    def test_ability_modifier_values(self):
        assert ability_modifier(10) == 0
        assert ability_modifier(18) == 4
        assert ability_modifier(8) == -1
        assert ability_modifier(1) == -5

    def test_valid_dice_notations(self):
        for notation in ["1d6", "2d8+3", "1d12+5", "8d6"]:
            total, rolls = parse_and_roll_dice(notation)
            assert total >= 1 and len(rolls) >= 1

    def test_invalid_dice_notation_raises(self):
        with pytest.raises(ValueError):
            parse_and_roll_dice("not-a-dice")

    def test_crit_doubles_dice_count(self):
        for _ in range(50):
            total, rolls = parse_and_roll_dice("1d6+3", crit=True)
            assert len(rolls) == 2
            assert total == sum(rolls) + 3

    def test_attack_roll_crit_and_fail_exclusive(self):
        with pytest.raises(ValueError, match="cannot be both"):
            AttackRoll(total=20, natural=20, is_crit=True, is_crit_fail=True)

    def test_combat_start_requires_player(self):
        with pytest.raises(ValueError):
            CombatStartPayload.model_validate({
                "combat_id": "test-01",
                "scene": {"description": "A dark room", "terrain": "dungeon_corridor",
                          "grid": {"width": 8, "height": 6}},
                "combatants": [
                    {"id": "e1", "name": "Goblin", "type": "enemy",
                     "position": {"x": 5, "y": 3},
                     "stats": {"hp": {"current": 7, "max": 7}, "ac": 15}},
                    {"id": "e2", "name": "Goblin2", "type": "enemy",
                     "position": {"x": 6, "y": 3},
                     "stats": {"hp": {"current": 7, "max": 7}, "ac": 15}},
                ],
                "narrative_context": {"preceding_summary": "Goblins appear."},
            })

    def test_victory_requires_survivor(self):
        with pytest.raises(ValueError, match="survivor"):
            CombatEndPayload(combat_id="x", duration_rounds=3,
                             outcome=CombatOutcome.victory, survivors=[])


class TestMockGemini:
    async def test_produces_valid_payload(self):
        payload = await trigger_combat_encounter(simulate_latency=False)
        assert isinstance(payload, CombatStartPayload)
        assert len(payload.combatants) >= 2

    async def test_combat_ids_are_unique(self):
        p1 = await trigger_combat_encounter(simulate_latency=False)
        p2 = await trigger_combat_encounter(simulate_latency=False)
        assert p1.combat_id != p2.combat_id

    async def test_wizard_has_spell_slots(self):
        payload = await trigger_combat_encounter(
            player_ids=["player_seraphina"], simulate_latency=False)
        seraphina = next(c for c in payload.combatants if c.id == "player_seraphina")
        assert seraphina.resources.spell_slots.level_3 == 2


class TestStateStore:
    async def test_create_and_retrieve(self, store, session):
        retrieved = await store.get(session.combat_id)
        assert retrieved is not None and retrieved.combat_id == session.combat_id

    async def test_get_unknown_returns_none(self, store):
        assert await store.get("nonexistent") is None

    async def test_duplicate_create_raises(self, store, session):
        with pytest.raises(ValueError, match="already exists"):
            await store.create(session)

    async def test_update_modifies_session(self, store, session):
        session.current_round = 5
        await store.update(session)
        assert (await store.get(session.combat_id)).current_round == 5

    async def test_delete_removes_session(self, store, session):
        assert await store.delete(session.combat_id) is True
        assert await store.get(session.combat_id) is None

    async def test_list_active_includes_session(self, store, session):
        active = await store.list_active()
        assert any(s.combat_id == session.combat_id for s in active)


class TestCombatEngine:
    async def test_initiative_covers_all_combatants(self, session, engine):
        assert set(session.initiative_order) == {c.id for c in session.start_payload.combatants}

    async def test_damage_reduces_hp(self, session, engine):
        target_id = session.start_payload.combatants[1].id
        target = engine._get_combatant(session, target_id)
        initial = target.stats.hp.current
        engine.apply_damage(session, target_id, 5)
        assert target.stats.hp.current == initial - 5

    async def test_damage_floors_at_zero(self, session, engine):
        target_id = session.start_payload.combatants[1].id
        engine.apply_damage(session, target_id, 9999)
        assert engine._get_combatant(session, target_id).stats.hp.current == 0

    async def test_healing_caps_at_max(self, session, engine):
        target_id = session.start_payload.combatants[0].id
        target = engine._get_combatant(session, target_id)
        result = engine.apply_healing(session, target_id, 9999)
        assert result.new_hp == target.stats.hp.max and result.overflow > 0

    async def test_attack_returns_valid_result(self, session, engine):
        attacker_id = session.start_payload.combatants[0].id
        target_id = session.start_payload.combatants[1].id
        ability_id = engine._get_combatant(session, attacker_id).abilities[0].id
        result = engine.resolve_attack(session, attacker_id, target_id, ability_id)
        assert 1 <= result.attack_roll_natural <= 20 and result.log_line

    async def test_victory_when_all_enemies_downed(self, session, engine):
        for c in session.start_payload.combatants:
            if c.type.value == "enemy":
                engine.apply_damage(session, c.id, 9999)
        assert engine.check_combat_end(session) == "victory"

    async def test_defeat_when_all_players_downed(self, session, engine):
        for c in session.start_payload.combatants:
            if c.type.value == "player":
                engine.apply_damage(session, c.id, 9999)
        assert engine.check_combat_end(session) == "defeat"

    async def test_combat_continues_when_all_alive(self, session, engine):
        assert engine.check_combat_end(session) is None


class TestCombatEndpoints:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200 and resp.json()["status"] == "ok"

    async def test_trigger_returns_active_session(self, client):
        resp = await client.post("/api/combat/trigger", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "combat_id" in data and data["status"] == "active"
        assert len(data["initiative_order"]) >= 2

    async def test_get_session_after_trigger(self, client):
        trigger = await client.post("/api/combat/trigger", json={})
        combat_id = trigger.json()["combat_id"]
        resp = await client.get(f"/api/combat/{combat_id}")
        assert resp.status_code == 200 and resp.json()["combat_id"] == combat_id

    async def test_get_unknown_returns_404(self, client):
        assert (await client.get("/api/combat/ghost")).status_code == 404

    async def test_full_pipeline(self, client):
        """trigger -> get id -> submit result."""
        combat_id = (await client.post("/api/combat/trigger", json={})).json()["combat_id"]
        result_payload = {
            "combat_id": combat_id,
            "duration_rounds": 4,
            "outcome": "victory",
            "survivors": [{"id": "player_aldric", "name": "Aldric",
                           "final_hp": 18, "max_hp": 52}],
            "defeated": [{"id": "enemy_goblin_boss", "name": "Goblin Boss",
                          "death_type": "killed", "killed_by": "player_aldric",
                          "killing_blow": "longsword_attack"}],
            "event_log": [{"round": 4, "turn": "player_aldric",
                           "action_id": "longsword_attack",
                           "target_id": "enemy_goblin_boss",
                           "attack_roll": {"total": 24, "natural": 20,
                                           "is_crit": True, "is_crit_fail": False},
                           "damage_dealt": 21, "narrative_tag": "killing_blow",
                           "detail": "Critical hit — Krax fell."}],
            "loot_acquired": [{"item": "Krax's Rusty Blade", "quantity": 1}],
            "dm_prompt_injection": "Aldric is wounded but victorious. Narrate this dramatically.",
        }
        resp = await client.post("/api/combat/result", json=result_payload)
        assert resp.status_code == 200 and resp.json()["outcome"] == "victory"

    async def test_result_unknown_session_404(self, client):
        resp = await client.post("/api/combat/result", json={
            "combat_id": "ghost", "duration_rounds": 1, "outcome": "draw"})
        assert resp.status_code == 404
