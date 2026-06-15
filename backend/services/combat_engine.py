"""D&D 5e Combat Engine — rule processor (Phase 1).

Decoupled from FastAPI, Gemini, and the client.
Knows only D&D 5e rules and CombatSession state.
Fully unit-testable without a running server.

Phase 1 coverage:
- Initiative rolling (d20 + DEX modifier)
- Attack resolution (vs AC, advantage/disadvantage)
- Damage calculation (dice parser, critical hit doubling)
- HP management (damage, healing)
- Combat end detection (victory / defeat)

Phase 2+ additions:
- Condition effects, saving throws, AoE, death saving throws
"""
from __future__ import annotations
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Optional
from backend.schemas.combat_session import CombatSession
from backend.schemas.combat_start import Ability, Combatant

logger = logging.getLogger(__name__)


@dataclass
class InitiativeResult:
    combatant_id: str
    name: str
    roll: int
    modifier: int
    total: int


@dataclass
class AttackResult:
    attacker_id: str
    target_id: str
    ability_id: str
    attack_roll_natural: int
    attack_roll_total: int
    target_ac: int
    hit: bool
    is_crit: bool
    is_crit_fail: bool
    damage_dealt: int = 0
    damage_dice_rolled: list[int] = field(default_factory=list)
    log_line: str = ""


@dataclass
class HealResult:
    target_id: str
    healing_done: int
    new_hp: int
    overflow: int


def roll_d20() -> int:
    return random.randint(1, 20)


def roll_die(sides: int) -> int:
    return random.randint(1, sides)


def parse_and_roll_dice(notation: str, crit: bool = False) -> tuple[int, list[int]]:
    """Parse dice notation and return (total, individual_rolls).

    Args:
        notation: e.g. '2d6+4', '1d8', '1d12+3'
        crit: If True, double the number of dice (D&D 5e critical hit rule).

    Returns:
        (total_damage, list_of_individual_rolls). Minimum total is 1.
    """
    pattern = r"^(\d+)d(\d+)(?:\+(\d+))?$"
    match = re.match(pattern, notation)
    if not match:
        raise ValueError(f"Invalid dice notation: '{notation}'")

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if crit:
        num_dice *= 2  # D&D 5e: double dice count, not the total

    rolls = [roll_die(die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    return max(total, 1), rolls


def ability_modifier(score: int) -> int:
    """D&D 5e ability modifier formula: (score - 10) // 2."""
    return (score - 10) // 2


class CombatEngine:
    """Stateless D&D 5e rule processor. Mutates CombatSession objects in place.

    All methods are synchronous — no I/O. Router layer handles async.
    """

    def roll_initiative_order(self, session: CombatSession) -> list[InitiativeResult]:
        """Roll initiative for all combatants. Sets session.initiative_order in place."""
        results: list[InitiativeResult] = []
        for combatant in session.start_payload.combatants:
            mod = ability_modifier(combatant.stats.ability_scores.dex)
            roll = roll_d20()
            total = roll + mod
            results.append(InitiativeResult(
                combatant_id=combatant.id, name=combatant.name,
                roll=roll, modifier=mod, total=total,
            ))
            logger.debug("Initiative: %s rolled %d + %d = %d", combatant.name, roll, mod, total)

        results.sort(key=lambda r: (r.total, random.random()), reverse=True)
        session.initiative_order = [r.combatant_id for r in results]
        session.current_turn_index = 0
        logger.info("Initiative order: %s", " -> ".join(r.name for r in results))
        return results

    def _get_combatant(self, session: CombatSession, combatant_id: str) -> Combatant:
        for c in session.start_payload.combatants:
            if c.id == combatant_id:
                return c
        raise ValueError(f"Combatant '{combatant_id}' not found in session")

    def _get_ability(self, combatant: Combatant, ability_id: str) -> Ability:
        for a in combatant.abilities:
            if a.id == ability_id:
                return a
        raise ValueError(f"Ability '{ability_id}' not found on '{combatant.id}'")

    def resolve_attack(
        self,
        session: CombatSession,
        attacker_id: str,
        target_id: str,
        ability_id: str,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> AttackResult:
        """Resolve a single attack roll and apply damage if it hits.

        D&D 5e rules:
        - Natural 20 = automatic hit + critical (double dice).
        - Natural 1  = automatic miss.
        - Advantage  = roll 2d20, take highest.
        - Disadvantage = roll 2d20, take lowest.
        - Advantage + Disadvantage cancel each other out.
        """
        attacker = self._get_combatant(session, attacker_id)
        target = self._get_combatant(session, target_id)
        ability = self._get_ability(attacker, ability_id)

        roll_adv = advantage and not disadvantage
        roll_dis = disadvantage and not advantage

        if roll_adv:
            natural = max(roll_d20(), roll_d20())
        elif roll_dis:
            natural = min(roll_d20(), roll_d20())
        else:
            natural = roll_d20()

        is_crit = natural == 20
        is_crit_fail = natural == 1
        attack_bonus = ability.attack_bonus or 0
        total_roll = natural + attack_bonus
        target_ac = target.stats.ac
        hit = is_crit or (not is_crit_fail and total_roll >= target_ac)

        damage_dealt = 0
        damage_rolls: list[int] = []
        if hit and ability.damage_dice:
            damage_dealt, damage_rolls = parse_and_roll_dice(ability.damage_dice, crit=is_crit)
            self.apply_damage(session, target_id, damage_dealt)

        roll_desc = f"nat {natural}" + (" (CRIT!)" if is_crit else " (MISS!)" if is_crit_fail else "")
        if hit and damage_dealt:
            log_line = (
                f"{attacker.name} attacks {target.name} with {ability.name}: "
                f"{roll_desc} -> {total_roll} vs AC {target_ac} -> HIT, "
                f"{damage_dealt} {ability.damage_type or ''} damage"
            )
        else:
            log_line = (
                f"{attacker.name} attacks {target.name} with {ability.name}: "
                f"{roll_desc} -> {total_roll} vs AC {target_ac} -> MISS"
            )

        logger.info(log_line)
        return AttackResult(
            attacker_id=attacker_id, target_id=target_id, ability_id=ability_id,
            attack_roll_natural=natural, attack_roll_total=total_roll,
            target_ac=target_ac, hit=hit, is_crit=is_crit, is_crit_fail=is_crit_fail,
            damage_dealt=damage_dealt, damage_dice_rolled=damage_rolls, log_line=log_line,
        )

    def apply_damage(self, session: CombatSession, target_id: str, amount: int) -> int:
        """Reduce target HP by amount (floor: 0). Returns new HP."""
        target = self._get_combatant(session, target_id)
        new_hp = max(0, target.stats.hp.current - amount)
        target.stats.hp.current = new_hp
        if new_hp == 0:
            logger.info("%s has been downed (0 HP)!", target.name)
        return new_hp

    def apply_healing(self, session: CombatSession, target_id: str, amount: int) -> HealResult:
        """Increase target HP (ceiling: max HP). Returns HealResult."""
        target = self._get_combatant(session, target_id)
        current = target.stats.hp.current
        max_hp = target.stats.hp.max
        new_hp = min(max_hp, current + amount)
        overflow = max(0, (current + amount) - max_hp)
        target.stats.hp.current = new_hp
        logger.info("%s healed for %d HP (%d -> %d)", target.name, amount - overflow, current, new_hp)
        return HealResult(target_id=target_id, healing_done=amount - overflow, new_hp=new_hp, overflow=overflow)

    def is_downed(self, combatant: Combatant) -> bool:
        return combatant.stats.hp.current == 0

    def get_active_combatants(self, session: CombatSession) -> list[Combatant]:
        return [c for c in session.start_payload.combatants if c.stats.hp.current > 0]

    def check_combat_end(self, session: CombatSession) -> Optional[str]:
        """Check if combat should end.

        Returns: 'victory', 'defeat', or None (combat continues).
        """
        from backend.schemas.combat_start import CombatantType
        active = self.get_active_combatants(session)
        active_types = {c.type for c in active}
        if CombatantType.enemy not in active_types:
            return "victory"
        if CombatantType.player not in active_types:
            return "defeat"
        return None


# Module-level singleton
combat_engine = CombatEngine()
