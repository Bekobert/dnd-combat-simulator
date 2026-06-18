/**
 * Zustand combat store — canonical client-side state.
 *
 * Single source of truth for both the React UI overlay and Phaser canvas.
 * Phaser reads from this store via direct import (not props),
 * keeping the canvas decoupled from React's render cycle.
 *
 * Flow:
 *   Backend / mock data → store actions → Phaser scene reacts → React UI rerenders
 */
import { create } from 'zustand';

const initialState = {
  combatId: null,
  status: 'idle', // idle | active | completed

  // Combatants keyed by id for O(1) lookup
  combatants: {},
  initiativeOrder: [],
  currentTurnIndex: 0,
  currentRound: 1,

  // UI
  selectedAbilityId: null,
  selectedTargetId: null,
  hoveredCombatantId: null,
  eventLog: [],
  isAnimating: false,
};

export const useCombatStore = create((set, get) => ({
  ...initialState,

  loadCombat: (payload) => {
    const combatants = {};
    for (const c of payload.combatants) {
      combatants[c.id] = { ...c, conditions: c.conditions ?? [] };
    }
    set({
      combatId: payload.combat_id,
      status: 'active',
      combatants,
      initiativeOrder: payload.initiative_order,
      currentTurnIndex: 0,
      currentRound: 1,
      eventLog: [],
      selectedAbilityId: null,
      selectedTargetId: null,
    });
  },

  endCombat: (outcome) => set({ status: 'completed', outcome }),

  advanceTurn: () => {
    const { initiativeOrder, currentTurnIndex, currentRound } = get();
    const nextIndex = (currentTurnIndex + 1) % initiativeOrder.length;
    const nextRound = nextIndex === 0 ? currentRound + 1 : currentRound;
    set({ currentTurnIndex: nextIndex, currentRound: nextRound, selectedAbilityId: null, selectedTargetId: null });
  },

  applyDamage: (targetId, amount) =>
    set((state) => {
      const t = state.combatants[targetId];
      if (!t) return state;
      return {
        combatants: {
          ...state.combatants,
          [targetId]: { ...t, stats: { ...t.stats, hp: { ...t.stats.hp, current: Math.max(0, t.stats.hp.current - amount) } } },
        },
      };
    }),

  applyHealing: (targetId, amount) =>
    set((state) => {
      const t = state.combatants[targetId];
      if (!t) return state;
      return {
        combatants: {
          ...state.combatants,
          [targetId]: { ...t, stats: { ...t.stats, hp: { ...t.stats.hp, current: Math.min(t.stats.hp.max, t.stats.hp.current + amount) } } },
        },
      };
    }),

  selectAbility: (id) => set({ selectedAbilityId: id, selectedTargetId: null }),
  selectTarget: (id) => set({ selectedTargetId: id }),
  hoverCombatant: (id) => set({ hoveredCombatantId: id }),
  setAnimating: (val) => set({ isAnimating: val }),

  addLogEntry: (entry) =>
    set((state) => ({ eventLog: [entry, ...state.eventLog].slice(0, 50) })),

  reset: () => set(initialState),
}));

export const selectCurrentCombatant = (state) =>
  state.combatants[state.initiativeOrder[state.currentTurnIndex]];

export const selectAllCombatants = (state) => Object.values(state.combatants);

export const selectIsMyTurn = (id) => (state) =>
  state.initiativeOrder[state.currentTurnIndex] === id;
