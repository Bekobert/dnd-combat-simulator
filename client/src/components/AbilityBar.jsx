/**
 * AbilityBar — shows the current combatant's abilities.
 * Only interactive on player turns (enemy turns handled by AI in Phase 4).
 */
import { useCombatStore, selectCurrentCombatant } from '../store/combatStore';

const ACTION_COST_COLOR = {
  action: '#4488ff',
  bonus_action: '#aa44ff',
  reaction: '#ff8844',
  free: '#44cc88',
  legendary: '#ffdd44',
};

export default function AbilityBar() {
  const current = useCombatStore(selectCurrentCombatant);
  const selectedAbilityId = useCombatStore((s) => s.selectedAbilityId);
  const selectedTargetId = useCombatStore((s) => s.selectedTargetId);
  const isAnimating = useCombatStore((s) => s.isAnimating);
  const selectAbility = useCombatStore((s) => s.selectAbility);
  const advanceTurn = useCombatStore((s) => s.advanceTurn);
  const applyDamage = useCombatStore((s) => s.applyDamage);
  const addLogEntry = useCombatStore((s) => s.addLogEntry);
  const currentRound = useCombatStore((s) => s.currentRound);

  if (!current || current.type !== 'player') {
    return (
      <div style={styles.container}>
        <span style={styles.waitText}>{current ? `${current.name}'s turn (AI)...` : 'Waiting...'}</span>
      </div>
    );
  }

  const handleUseAbility = () => {
    if (!selectedAbilityId || !selectedTargetId || isAnimating) return;
    const ability = current.abilities.find((a) => a.id === selectedAbilityId);
    if (!ability) return;

    const rollDice = (notation) => {
      if (!notation) return 0;
      const match = notation.match(/^(\d+)d(\d+)(?:\+(\d+))?$/);
      if (!match) return 0;
      const [, numDice, dieSides, mod] = match.map(Number);
      let total = mod || 0;
      for (let i = 0; i < numDice; i++) total += Math.floor(Math.random() * dieSides) + 1;
      return total;
    };

    const damage = rollDice(ability.damage_dice);
    if (damage > 0) applyDamage(selectedTargetId, damage);

    addLogEntry({
      round: currentRound,
      text: `${current.name} uses ${ability.name}${damage > 0 ? ` -> ${damage} damage` : ''}`,
      tag: damage > 0 ? 'solid_hit' : 'action',
    });

    advanceTurn();
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.turnLabel}>{current.name}'s Turn</span>
        <span style={styles.hpLabel}>HP: {current.stats.hp.current}/{current.stats.hp.max}</span>
      </div>

      <div style={styles.abilities}>
        {current.abilities.map((ability) => {
          const isSelected = selectedAbilityId === ability.id;
          const acColor = ACTION_COST_COLOR[ability.action_cost] ?? '#888';
          return (
            <button
              key={ability.id}
              onClick={() => selectAbility(ability.id)}
              style={{ ...styles.abilityBtn, ...(isSelected ? styles.abilityBtnSelected : {}), borderColor: isSelected ? acColor : '#333' }}
              title={ability.description ?? ability.name}
            >
              <span style={{ ...styles.actionCostDot, background: acColor }} />
              <span style={styles.abilityName}>{ability.name}</span>
              {ability.damage_dice && <span style={styles.damageDice}>{ability.damage_dice}</span>}
            </button>
          );
        })}
      </div>

      <div style={styles.actions}>
        <button
          onClick={handleUseAbility}
          disabled={!selectedAbilityId || !selectedTargetId || isAnimating}
          style={{ ...styles.actionBtn, ...(!selectedAbilityId || !selectedTargetId ? styles.actionBtnDisabled : styles.actionBtnReady) }}
        >
          {selectedAbilityId && selectedTargetId ? 'Execute' : 'Select ability + target'}
        </button>
        <button onClick={advanceTurn} style={styles.skipBtn}>Skip Turn -></button>
      </div>

      {selectedTargetId && (
        <div style={styles.targetLabel}>Target: {selectedTargetId.replace('enemy_', '').replace('_', ' ')}</div>
      )}
    </div>
  );
}

const styles = {
  container: { background: 'rgba(10,10,20,0.95)', border: '1px solid #333', borderRadius: 8, padding: '10px 14px', fontFamily: 'monospace', minHeight: 80 },
  header: { display: 'flex', justifyContent: 'space-between', marginBottom: 8 },
  turnLabel: { fontSize: 13, color: '#ffdd44', fontWeight: 'bold' },
  hpLabel: { fontSize: 12, color: '#aaa' },
  abilities: { display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 },
  abilityBtn: { display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', background: 'rgba(255,255,255,0.04)', border: '1px solid #333', borderRadius: 5, color: '#ddd', fontSize: 12, cursor: 'pointer' },
  abilityBtnSelected: { background: 'rgba(255,221,68,0.12)' },
  actionCostDot: { width: 7, height: 7, borderRadius: '50%', flexShrink: 0 },
  abilityName: { color: '#eee' },
  damageDice: { fontSize: 10, color: '#888', marginLeft: 2 },
  actions: { display: 'flex', gap: 8 },
  actionBtn: { flex: 1, padding: '7px 0', borderRadius: 5, border: 'none', cursor: 'pointer', fontSize: 13, fontFamily: 'monospace', fontWeight: 'bold' },
  actionBtnReady: { background: '#cc3333', color: '#fff' },
  actionBtnDisabled: { background: '#222', color: '#555', cursor: 'not-allowed' },
  skipBtn: { padding: '7px 14px', borderRadius: 5, background: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer', fontSize: 12, fontFamily: 'monospace' },
  waitText: { color: '#888', fontSize: 13 },
  targetLabel: { marginTop: 6, fontSize: 11, color: '#ff8888' },
};
