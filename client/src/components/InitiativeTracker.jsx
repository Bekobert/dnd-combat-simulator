/**
 * InitiativeTracker — React UI overlay showing turn order.
 * Reads from Zustand store; no props needed.
 */
import { useCombatStore } from '../store/combatStore';

export default function InitiativeTracker() {
  const initiativeOrder = useCombatStore((s) => s.initiativeOrder);
  const currentTurnIndex = useCombatStore((s) => s.currentTurnIndex);
  const combatants = useCombatStore((s) => s.combatants);
  const currentRound = useCombatStore((s) => s.currentRound);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.roundLabel}>Round {currentRound}</span>
        <span style={styles.title}>Initiative</span>
      </div>
      <div style={styles.list}>
        {initiativeOrder.map((id, idx) => {
          const c = combatants[id];
          if (!c) return null;
          const isCurrent = idx === currentTurnIndex;
          const isDowned = c.stats.hp.current === 0;
          const isPlayer = c.type === 'player';
          const hpPct = c.stats.hp.current / c.stats.hp.max;
          return (
            <div key={id} style={{ ...styles.entry, ...(isCurrent ? styles.entryActive : {}), ...(isDowned ? styles.entryDowned : {}) }}>
              <span style={styles.turnIndicator}>{isCurrent ? '>' : String(idx + 1)}</span>
              <span style={{ ...styles.avatar, background: isPlayer ? '#2255aa' : '#aa2222', border: isCurrent ? '2px solid #ffdd44' : '2px solid #444' }}>
                {isDowned ? 'X' : c.name[0]}
              </span>
              <div style={styles.info}>
                <span style={{ ...styles.name, color: isPlayer ? '#88aaff' : '#ff8888' }}>{c.name}</span>
                <div style={styles.hpTrack}>
                  <div style={{ ...styles.hpFill, width: `${hpPct * 100}%`, background: hpPct > 0.5 ? '#22cc44' : hpPct > 0.25 ? '#ddaa00' : '#ee2222' }} />
                </div>
                <span style={styles.hpText}>{c.stats.hp.current}/{c.stats.hp.max}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  container: { width: 180, background: 'rgba(10,10,20,0.92)', border: '1px solid #333', borderRadius: 8, padding: '8px 0', fontFamily: 'monospace' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 10px 6px', borderBottom: '1px solid #333', marginBottom: 4 },
  title: { fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1 },
  roundLabel: { fontSize: 11, color: '#ffdd44', fontWeight: 'bold' },
  list: { display: 'flex', flexDirection: 'column', gap: 2 },
  entry: { display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px', borderRadius: 4 },
  entryActive: { background: 'rgba(255,221,68,0.1)', border: '1px solid rgba(255,221,68,0.3)' },
  entryDowned: { opacity: 0.4 },
  turnIndicator: { fontSize: 10, color: '#ffdd44', width: 12, textAlign: 'center' },
  avatar: { width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 'bold', color: '#fff', flexShrink: 0 },
  info: { flex: 1, display: 'flex', flexDirection: 'column', gap: 2 },
  name: { fontSize: 11, fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  hpTrack: { height: 4, background: '#222', borderRadius: 2, overflow: 'hidden' },
  hpFill: { height: '100%', borderRadius: 2, transition: 'width 0.4s ease, background 0.3s' },
  hpText: { fontSize: 9, color: '#666' },
};
