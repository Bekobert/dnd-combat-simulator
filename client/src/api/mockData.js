/**
 * Mock combat data — used in Phase 2 while the backend SSE bridge (Phase 3) is pending.
 * Shape matches CombatStartPayload exactly so swapping to real API needs zero store changes.
 */
export const MOCK_COMBAT_PAYLOAD = {
  combat_id: 'mock-session-001',
  scene: {
    description: 'A narrow dungeon corridor before the goblin throne',
    terrain: 'dungeon_corridor',
    grid: { width: 12, height: 8, tile_size: 64 },
  },
  combatants: [
    {
      id: 'player_aldric', name: 'Aldric', type: 'player',
      class: 'Fighter', level: 5, sprite: 'fighter',
      position: { x: 2, y: 3 },
      stats: { hp: { current: 42, max: 52 }, ac: 17, speed: 30,
               ability_scores: { str: 18, dex: 12, con: 16, int: 8, wis: 10, cha: 10 } },
      resources: { action: true, bonus_action: true, reaction: true, spell_slots: {},
                   named: { second_wind: { uses_remaining: 1, max: 1 }, action_surge: { uses_remaining: 1, max: 1 } } },
      conditions: [],
      abilities: [
        { id: 'longsword_attack', name: 'Longsword', action_cost: 'action', range_ft: 5, damage_dice: '1d8+4', damage_type: 'slashing', attack_bonus: 7 },
        { id: 'second_wind', name: 'Second Wind', action_cost: 'bonus_action', range_ft: 0, description: 'Regain 1d10+5 HP' },
        { id: 'action_surge', name: 'Action Surge', action_cost: 'free', range_ft: 0, description: 'Extra action this turn' },
      ],
    },
    {
      id: 'player_seraphina', name: 'Seraphina', type: 'player',
      class: 'Wizard', level: 5, sprite: 'wizard',
      position: { x: 2, y: 5 },
      stats: { hp: { current: 28, max: 28 }, ac: 13, speed: 30,
               ability_scores: { str: 8, dex: 14, con: 12, int: 18, wis: 12, cha: 10 } },
      resources: { action: true, bonus_action: true, reaction: true,
                   spell_slots: { level_1: 4, level_2: 3, level_3: 2 }, named: {} },
      conditions: [],
      abilities: [
        { id: 'fireball', name: 'Fireball', action_cost: 'action', range_ft: 150, damage_dice: '8d6', damage_type: 'fire', spell_level: 3, save_dc: 15 },
        { id: 'magic_missile', name: 'Magic Missile', action_cost: 'action', range_ft: 120, damage_dice: '3d4', damage_type: 'force', spell_level: 1 },
      ],
    },
    {
      id: 'enemy_goblin_boss', name: 'Goblin Boss', type: 'enemy',
      sprite: 'goblin', position: { x: 9, y: 3 },
      stats: { hp: { current: 21, max: 21 }, ac: 15, speed: 30,
               ability_scores: { str: 8, dex: 14, con: 10, int: 8, wis: 8, cha: 8 } },
      resources: { action: true, bonus_action: true, reaction: true, spell_slots: {}, named: {} },
      conditions: [],
      abilities: [
        { id: 'scimitar', name: 'Scimitar', action_cost: 'action', range_ft: 5, damage_dice: '1d6+2', damage_type: 'slashing', attack_bonus: 4 },
        { id: 'nimble_escape', name: 'Nimble Escape', action_cost: 'bonus_action', range_ft: 0 },
      ],
      ai_behavior: 'aggressive', cr: 1,
    },
    {
      id: 'enemy_orc', name: 'Orc Warrior', type: 'enemy',
      sprite: 'orc', position: { x: 9, y: 5 },
      stats: { hp: { current: 15, max: 15 }, ac: 13, speed: 30,
               ability_scores: { str: 16, dex: 10, con: 14, int: 7, wis: 9, cha: 8 } },
      resources: { action: true, bonus_action: true, reaction: true, spell_slots: {}, named: {} },
      conditions: [],
      abilities: [
        { id: 'greataxe', name: 'Greataxe', action_cost: 'action', range_ft: 5, damage_dice: '1d12+3', damage_type: 'slashing', attack_bonus: 5 },
      ],
      ai_behavior: 'berserker', cr: 0.5,
    },
  ],
  initiative_order: ['player_aldric', 'enemy_goblin_boss', 'player_seraphina', 'enemy_orc'],
  narrative_context: {
    preceding_summary: 'The party pushed open the rusted iron door and met Goblin Chief Krax.',
  },
};
