/**
 * GridScene — main Phaser 3 combat scene.
 *
 * Responsibilities:
 * - Render the dungeon grid (tile-based, checkerboard pattern)
 * - Place combatant sprites on their grid positions
 * - Draw HP bars above each sprite
 * - Highlight: current turn (gold pulse), hovered tile, valid targets (red flash)
 * - Write to Zustand store on sprite click (selectTarget)
 * - Subscribe to store changes: HP updates, turn changes
 *
 * Architecture:
 * Scene reads from store via getState() and subscribe().
 * Never triggers React rerenders directly — all mutations go through store actions.
 */
import Phaser from 'phaser';
import { useCombatStore } from '../../store/combatStore';

export const TILE_SIZE = 64;
const GRID_OFFSET_X = 40;
const GRID_OFFSET_Y = 40;

const COLORS = {
  tileLight:    0x2a1a0e,
  tileDark:     0x1e1208,
  tileHover:    0x4a3520,
  hpFull:       0x22cc44,
  hpMid:        0xddaa00,
  hpLow:        0xee2222,
  hpBackground: 0x111111,
  outline:      0x888888,
  gold:         0xffdd44,
  white:        0xffffff,
};

export default class GridScene extends Phaser.Scene {
  constructor() {
    super({ key: 'GridScene' });
    this.gridWidth = 12;
    this.gridHeight = 8;
    this.tiles = [];
    this.spriteObjects = {};
    this.hoveredTile = null;
    this._unsubscribe = null;
  }

  init(data) {
    if (data.gridWidth)  this.gridWidth  = data.gridWidth;
    if (data.gridHeight) this.gridHeight = data.gridHeight;
  }

  create() {
    this._buildGrid();
    this._buildCombatants();
    this._setupInput();
    this._subscribeToStore();
    this._startIdleAnimations();
  }

  destroy() {
    if (this._unsubscribe) this._unsubscribe();
    super.destroy();
  }

  // ── Grid ─────────────────────────────────────────────────────────

  _buildGrid() {
    this.tiles = [];
    for (let row = 0; row < this.gridHeight; row++) {
      this.tiles[row] = [];
      for (let col = 0; col < this.gridWidth; col++) {
        const x = GRID_OFFSET_X + col * TILE_SIZE;
        const y = GRID_OFFSET_Y + row * TILE_SIZE;
        const isDark = (row + col) % 2 === 0;
        const tile = this.add.rectangle(
          x + TILE_SIZE / 2, y + TILE_SIZE / 2,
          TILE_SIZE - 2, TILE_SIZE - 2,
          isDark ? COLORS.tileDark : COLORS.tileLight,
        );
        tile.setStrokeStyle(1, COLORS.outline, 0.3);
        tile.setInteractive();
        tile._col = col;
        tile._row = row;
        tile._baseColor = isDark ? COLORS.tileDark : COLORS.tileLight;
        this.tiles[row][col] = tile;
      }
    }
  }

  _getTile(col, row) { return this.tiles[row]?.[col] ?? null; }

  _worldToGrid(worldX, worldY) {
    return {
      col: Math.floor((worldX - GRID_OFFSET_X) / TILE_SIZE),
      row: Math.floor((worldY - GRID_OFFSET_Y) / TILE_SIZE),
    };
  }

  gridToWorld(col, row) {
    return {
      x: GRID_OFFSET_X + col * TILE_SIZE + TILE_SIZE / 2,
      y: GRID_OFFSET_Y + row * TILE_SIZE + TILE_SIZE / 2,
    };
  }

  // ── Combatants ────────────────────────────────────────────────────

  _buildCombatants() {
    const { combatants } = useCombatStore.getState();
    this.spriteObjects = {};
    for (const c of Object.values(combatants)) {
      this._createCombatantSprite(c);
    }
  }

  _createCombatantSprite(combatant) {
    const { x, y } = this.gridToWorld(combatant.position.x, combatant.position.y);
    const isPlayer = combatant.type === 'player';
    const size = TILE_SIZE * 0.55;

    let body;
    if (isPlayer) {
      body = this.add.circle(0, 0, size / 2, 0x2255aa);
    } else {
      body = this.add.rectangle(0, 0, size * 0.7, size * 0.7, 0xaa2222);
      body.setRotation(Math.PI / 4);
    }
    body.setStrokeStyle(2, isPlayer ? COLORS.gold : COLORS.white, 0.9);

    const label = this.add.text(0, 0, combatant.name[0].toUpperCase(), {
      fontSize: '18px', fontFamily: 'monospace', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5);

    const hpBarWidth = TILE_SIZE - 8;
    const hpBg  = this.add.rectangle(0, -size / 2 - 10, hpBarWidth, 6, COLORS.hpBackground);
    const hpBar = this.add.rectangle(-hpBarWidth / 2, -size / 2 - 10, hpBarWidth, 6, COLORS.hpFull).setOrigin(0, 0.5);

    const nameTag = this.add.text(0, size / 2 + 8, combatant.name, {
      fontSize: '10px', fontFamily: 'monospace',
      color: isPlayer ? '#88aaff' : '#ff8888',
    }).setOrigin(0.5);

    const container = this.add.container(x, y, [hpBg, hpBar, body, label, nameTag]);
    container.setSize(TILE_SIZE, TILE_SIZE);
    container.setInteractive();
    container._combatantId = combatant.id;

    this.spriteObjects[combatant.id] = { container, body, label, hpBar, hpBg, nameTag, size };
    this._updateHpBar(combatant.id);
  }

  // ── HP bar ────────────────────────────────────────────────────────

  _updateHpBar(combatantId) {
    const obj = this.spriteObjects[combatantId];
    if (!obj) return;
    const c = useCombatStore.getState().combatants[combatantId];
    if (!c) return;

    const pct = c.stats.hp.current / c.stats.hp.max;
    const color = pct > 0.5 ? COLORS.hpFull : pct > 0.25 ? COLORS.hpMid : COLORS.hpLow;
    obj.hpBar.setFillStyle(color);
    obj.hpBar.width = Math.max(0, (TILE_SIZE - 8) * pct);

    if (c.stats.hp.current === 0) {
      obj.body.setAlpha(0.35);
      obj.label.setText('X');
    }
  }

  // ── Turn highlight ────────────────────────────────────────────────

  _highlightCurrentTurn(combatantId) {
    for (const [id, obj] of Object.entries(this.spriteObjects)) {
      obj.body.setStrokeStyle(2, id === combatantId ? COLORS.gold : COLORS.white, 0.9);
    }
    const obj = this.spriteObjects[combatantId];
    if (!obj) return;
    this.tweens.add({ targets: obj.container, scaleX: 1.12, scaleY: 1.12, duration: 400, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
  }

  _clearTurnHighlight(combatantId) {
    const obj = this.spriteObjects[combatantId];
    if (!obj) return;
    this.tweens.killTweensOf(obj.container);
    obj.container.setScale(1);
  }

  // ── Input ─────────────────────────────────────────────────────────

  _setupInput() {
    this.input.on('pointermove', (pointer) => {
      if (this.hoveredTile) this.hoveredTile.setFillStyle(this.hoveredTile._baseColor);
      const { col, row } = this._worldToGrid(pointer.x, pointer.y);
      const tile = this._getTile(col, row);
      if (tile) { tile.setFillStyle(COLORS.tileHover); this.hoveredTile = tile; }
    });

    for (const [id, obj] of Object.entries(this.spriteObjects)) {
      obj.container.on('pointerdown', () => {
        const { combatants, selectTarget, hoverCombatant } = useCombatStore.getState();
        const c = combatants[id];
        if (!c) return;
        if (c.type === 'enemy') { selectTarget(id); this._flashSprite(id, 0xff4444); }
        else { hoverCombatant(id); }
      });
      obj.container.on('pointerover', () => { useCombatStore.getState().hoverCombatant(id); obj.container.setScale(1.08); });
      obj.container.on('pointerout',  () => { useCombatStore.getState().hoverCombatant(null); obj.container.setScale(1); });
    }
  }

  // ── Animations ────────────────────────────────────────────────────

  _flashSprite(id, color) {
    const obj = this.spriteObjects[id];
    if (!obj) return;
    this.tweens.add({ targets: obj.body, fillColor: color, duration: 120, yoyo: true, repeat: 2 });
  }

  showDamageNumber(combatantId, amount, isHeal = false) {
    const obj = this.spriteObjects[combatantId];
    if (!obj) return;
    const { x, y } = obj.container;
    const text = this.add.text(x, y - 20, isHeal ? `+${amount}` : `-${amount}`, {
      fontSize: '22px', fontFamily: 'monospace',
      color: isHeal ? '#44ff88' : '#ff4444',
      fontStyle: 'bold', stroke: '#000000', strokeThickness: 3,
    }).setOrigin(0.5);
    this.tweens.add({ targets: text, y: y - 70, alpha: 0, duration: 900, ease: 'Cubic.easeOut', onComplete: () => text.destroy() });
  }

  _startIdleAnimations() {
    const { combatants } = useCombatStore.getState();
    for (const [id, obj] of Object.entries(this.spriteObjects)) {
      if (combatants[id]?.type === 'player') {
        this.tweens.add({
          targets: obj.container, y: obj.container.y - 4,
          duration: 1200 + Math.random() * 400,
          yoyo: true, repeat: -1, ease: 'Sine.easeInOut', delay: Math.random() * 600,
        });
      }
    }
  }

  // ── Store subscription ────────────────────────────────────────────

  _subscribeToStore() {
    let prev = useCombatStore.getState();
    this._unsubscribe = useCombatStore.subscribe((state) => {
      for (const id of Object.keys(state.combatants)) {
        const pC = prev.combatants[id];
        const cC = state.combatants[id];
        if (!pC || !cC) continue;
        if (pC.stats.hp.current !== cC.stats.hp.current) {
          const diff = pC.stats.hp.current - cC.stats.hp.current;
          this._updateHpBar(id);
          if (diff > 0) this.showDamageNumber(id, diff, false);
          if (diff < 0) this.showDamageNumber(id, Math.abs(diff), true);
        }
      }
      const prevId = prev.initiativeOrder[prev.currentTurnIndex];
      const currId = state.initiativeOrder[state.currentTurnIndex];
      if (prevId !== currId) {
        if (prevId) this._clearTurnHighlight(prevId);
        if (currId) this._highlightCurrentTurn(currId);
      }
      prev = state;
    });
    const { initiativeOrder, currentTurnIndex } = useCombatStore.getState();
    if (initiativeOrder[currentTurnIndex]) this._highlightCurrentTurn(initiativeOrder[currentTurnIndex]);
  }
}
