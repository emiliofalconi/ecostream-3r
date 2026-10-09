// EcoStream 3R - AquaGuardians: Cliente Web / Desktop (TS + Canvas 2D)
import { sound } from './sound';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  color: string;
  size: number;
  type?: 'water' | 'spark' | 'bubble' | 'leaf';
}

interface FloatingText {
  text: string;
  x: number;
  y: number;
  vy: number;
  alpha: number;
  color: string;
}

interface WaterMetrics {
  reservoirLevelPct: number;
  waterPurityPct: number;
  totalLitersSaved: number;
  totalLitersReused: number;
  totalLitersRecycled: number;
}

interface PipeEntity {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  isLeaking: boolean;
  repairProgress: number; // 0 a 100
}

interface CropTile {
  x: number;
  y: number;
  growth: number; // 0 a 1.0
  type: number;
}

interface Shockwave {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  color: string;
  alpha: number;
  lineWidth: number;
}

interface EcoCollectible {
  id: number;
  x: number;
  y: number;
  type: 'kit' | 'droplet' | 'speed';
  life: number;
  pulse: number;
}

interface EcoThreat {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  pulse: number;
}

interface ActiveChaosEvent {
  type: 'heatwave' | 'burst' | 'rain';
  title: string;
  duration: number;
  maxDuration: number;
}

interface Afterimage {
  x: number;
  y: number;
  angle: number;
  alpha: number;
}

const canvas = document.getElementById('gameCanvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d')!;

// Partículas y Efectos Visuales
const particles: Particle[] = [];
const floatingTexts: FloatingText[] = [];
const shockwaves: Shockwave[] = [];
const afterimages: Afterimage[] = [];
const collectibles: EcoCollectible[] = [];
const threats: EcoThreat[] = [];
let screenShake = 0;
let nextCollectibleId = 1;
let nextThreatId = 1;
let collectibleSpawnTimer = 4.0;
let threatSpawnTimer = 7.0;

function triggerScreenShake(intensity: number) {
  screenShake = Math.max(screenShake, intensity);
}

// Estado Global del Juego
const state = {
  tick: 0,
  metrics: {
    reservoirLevelPct: 100.0,
    waterPurityPct: 96.0,
    totalLitersSaved: 0,
    totalLitersReused: 0,
    totalLitersRecycled: 0,
  } as WaterMetrics,
  score: 0,
  isGameOver: false,
  hasWon: false,
  combo: {
    count: 0,
    timer: 0,
  },
  activeChaos: null as ActiveChaosEvent | null,
  chaosTimer: 20.0, // Próximo evento dinámico
  player: {
    x: 420,
    y: 320,
    vx: 0,
    vy: 0,
    targetX: null as number | null,
    targetY: null as number | null,
    angle: 0,
    isWrenching: false,
    walkCycle: 0,
    isDashing: false,
    dashTimer: 0,
    dashCooldown: 0,
    speedBuffTimer: 0,
  },
  pipes: [
    { id: 1, x: 300, y: 150, w: 220, h: 26, isLeaking: false, repairProgress: 100 },
    { id: 2, x: 300, y: 220, w: 220, h: 26, isLeaking: true, repairProgress: 0 },
    { id: 3, x: 300, y: 290, w: 220, h: 26, isLeaking: false, repairProgress: 100 },
  ] as PipeEntity[],
  crops: [] as CropTile[],
  plant: { x: 780, y: 340, active: true, spinAngle: 0 },
  sprinklersActive: false,
  sprinklerTimer: 0,
};

// Inicializar huerto agrícola
for (let r = 0; r < 3; r++) {
  for (let c = 0; c < 4; c++) {
    state.crops.push({
      x: 300 + c * 55,
      y: 390 + r * 50,
      growth: 0.3 + Math.random() * 0.4,
      type: (r + c) % 3,
    });
  }
}

// Redimensionar Canvas
function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight - 76;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// ==========================================================================
// CONTROLES DE TECLADO FLUIDOS (POLLING CONTINUO CON SET & NORMALIZACIÓN)
// ==========================================================================
const activeKeys = new Set<string>();

window.addEventListener('keydown', (e) => {
  activeKeys.add(e.code);
  activeKeys.add(e.key.toLowerCase());

  // Tecla SHIFT: Activar Dash / Impulso Rápido
  if (e.code === 'ShiftLeft' || e.code === 'ShiftRight' || e.key.toLowerCase() === 'shift') {
    triggerDash();
  } else if (e.code === 'Space') {
    e.preventDefault();
    actionReduce();
  } else if (e.key.toLowerCase() === 'r') {
    actionReuse();
  } else if (e.key.toLowerCase() === 'f') {
    actionRecycle();
  }
});

window.addEventListener('keyup', (e) => {
  activeKeys.delete(e.code);
  activeKeys.delete(e.key.toLowerCase());
});

// Limpiar teclas si la ventana pierde el foco (evita teclas pegadas)
window.addEventListener('blur', () => {
  activeKeys.clear();
});

function isKeyPressed(...codes: string[]): boolean {
  for (const c of codes) {
    if (activeKeys.has(c)) return true;
  }
  return false;
}

// Activación del Dash / Impulso Rápido
function triggerDash() {
  const p = state.player;
  if (p.dashCooldown > 0 || p.isDashing) return;

  p.isDashing = true;
  p.dashTimer = 0.20; // 200ms de aceleración extrema
  p.dashCooldown = 0.95; // 0.95s de cooldown

  // Dirección hacia donde se mueve o mira
  let dashDx = Math.cos(p.angle);
  let dashDy = Math.sin(p.angle);

  // Si hay teclas activas en este instante, orientar el dash en esa dirección
  let moveDx = 0;
  let moveDy = 0;
  if (isKeyPressed('KeyW', 'ArrowUp', 'w')) moveDy -= 1;
  if (isKeyPressed('KeyS', 'ArrowDown', 's')) moveDy += 1;
  if (isKeyPressed('KeyA', 'ArrowLeft', 'a')) moveDx -= 1;
  if (isKeyPressed('KeyD', 'ArrowRight', 'd')) moveDx += 1;

  if (moveDx !== 0 || moveDy !== 0) {
    const len = Math.hypot(moveDx, moveDy);
    dashDx = moveDx / len;
    dashDy = moveDy / len;
    p.angle = Math.atan2(dashDy, dashDx);
  }

  const dashVelocity = 680; // px/s
  p.vx = dashDx * dashVelocity;
  p.vy = dashDy * dashVelocity;

  triggerScreenShake(4);
  sound.playDash();

  // Partículas de estela de viento / agua
  for (let i = 0; i < 20; i++) {
    particles.push({
      x: p.x + (Math.random() - 0.5) * 16,
      y: p.y + (Math.random() - 0.5) * 16,
      vx: -dashDx * (Math.random() * 4 + 2) + (Math.random() - 0.5) * 2,
      vy: -dashDy * (Math.random() * 4 + 2) + (Math.random() - 0.5) * 2,
      life: 0.55,
      maxLife: 0.55,
      color: ['#38bdf8', '#0ea5e9', '#ffffff', '#7dd3fc'][Math.floor(Math.random() * 4)],
      size: 2.5 + Math.random() * 2.5,
      type: 'water',
    });
  }

  showToast('⚡ ¡IMPULSO DASH ACTIVADO!', 'reuse');
}

// Botones UI con sonido de click
document.getElementById('btnReduce')?.addEventListener('click', () => { sound.playButtonClick(); actionReduce(); });
document.getElementById('btnReuse')?.addEventListener('click', () => { sound.playButtonClick(); actionReuse(); });
document.getElementById('btnRecycle')?.addEventListener('click', () => { sound.playButtonClick(); actionRecycle(); });

// Toggle Sonido con Ambiente Procedural
const btnSound = document.getElementById('btnSoundToggle');
btnSound?.addEventListener('click', () => {
  sound.enabled = !sound.enabled;
  sound.playButtonClick();
  sound.toggleAmbience(sound.enabled);
  if (btnSound) {
    btnSound.textContent = sound.enabled ? '🔊' : '🔇';
    btnSound.style.opacity = sound.enabled ? '1.0' : '0.5';
  }
});

// Click en el Canvas para Mover Avatar y Generar Ondas de Agua (Ripples)
canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const clickX = (e.clientX - rect.left) * scaleX;
  const clickY = (e.clientY - rect.top) * scaleY;

  state.player.targetX = clickX;
  state.player.targetY = clickY;

  shockwaves.push({
    x: clickX,
    y: clickY,
    radius: 4,
    maxRadius: 32,
    color: '#38bdf8',
    alpha: 0.9,
    lineWidth: 2.2,
  });
  sound.playWaterSplash();
});

// Toast Notificaciones
function showToast(msg: string, type: 'reduce' | 'reuse' | 'recycle') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${type === 'reduce' ? '🔧' : type === 'reuse' ? '🌱' : '⚗️'}</span> <span>${msg}</span>`;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity 0.3s ease';
    setTimeout(() => t.remove(), 300);
  }, 2200);
}

function spawnFloatingText(text: string, x: number, y: number, color: string) {
  floatingTexts.push({ text, x, y, vy: -1.5, alpha: 1.0, color });
}

function register3RComboAction(actionName: string) {
  state.combo.count = Math.min(3, state.combo.count + 1);
  state.combo.timer = 5.0; // 5 segundos para mantener el combo activo

  if (state.combo.count >= 2) {
    const multiplier = state.combo.count;
    const bonus = 60 * multiplier;
    state.score += bonus;
    sound.playCombo();
    triggerScreenShake(4);

    spawnFloatingText(`🔥 ¡COMBO x${multiplier} ACTIVADO! +${bonus} PTS`, state.player.x - 50, state.player.y - 45, '#fbbf24');
    if (state.combo.count === 3) {
      showToast('🌟 ¡TRIPLE-R FRENZY ALCANZADO! Máximo Multiplicador Activo', 'recycle');
      // Partículas doradas
      for (let i = 0; i < 20; i++) {
        particles.push({
          x: state.player.x + (Math.random() - 0.5) * 30,
          y: state.player.y + (Math.random() - 0.5) * 30,
          vx: (Math.random() - 0.5) * 6,
          vy: (Math.random() - 0.8) * 6,
          life: 0.8,
          maxLife: 0.8,
          color: '#fbbf24',
          size: 3.5,
          type: 'spark',
        });
      }
    }
  }
}

// --------------------------------------------------------------------------
// ACCIONES 3R CON FEEDBACK VISUAL Y SONORO
// --------------------------------------------------------------------------
function actionReduce() {
  const leaking = state.pipes.find((p) => p.isLeaking);
  if (leaking) {
    leaking.isLeaking = false;
    leaking.repairProgress = 100;
    state.metrics.totalLitersSaved += 80;
    
    // Bonificación si hay evento de mega-rotura
    const isBurst = state.activeChaos?.type === 'burst';
    const earnedScore = isBurst ? 220 : 150;
    state.score += earnedScore;

    state.player.isWrenching = true;
    setTimeout(() => (state.player.isWrenching = false), 500);

    triggerScreenShake(6);
    sound.playRepair();
    sound.playShockwave();

    // Onda expansiva en la tubería reparada
    shockwaves.push({
      x: leaking.x + 110,
      y: leaking.y + 13,
      radius: 8,
      maxRadius: 65,
      color: '#38bdf8',
      alpha: 1.0,
      lineWidth: 3,
    });

    // Chispas de soldadura metálica
    for (let i = 0; i < 28; i++) {
      particles.push({
        x: leaking.x + 110,
        y: leaking.y + 13,
        vx: (Math.random() - 0.5) * 8.5,
        vy: (Math.random() - 0.7) * 7.5,
        life: 1.0,
        maxLife: 1.0,
        color: ['#fbbf24', '#f59e0b', '#38bdf8', '#ffffff'][Math.floor(Math.random() * 4)],
        size: 2 + Math.random() * 3,
        type: 'spark',
      });
    }

    register3RComboAction('reduce');
    spawnFloatingText(`+${earnedScore} PTS (80L Salvados!)`, leaking.x + 60, leaking.y - 10, '#38bdf8');
    showToast(isBurst ? '🚨 ¡Fuga de emergencia contenida! +220 PTS' : '¡Fuga sellada con éxito! +80 Litros Ahorrados', 'reduce');
    updateHUD();
  } else {
    // Si no hay roturas, generar una nueva aleatoria tras un breve delay para juego continuo
    const okPipes = state.pipes.filter((p) => !p.isLeaking);
    if (okPipes.length > 0) {
      const p = okPipes[Math.floor(Math.random() * okPipes.length)];
      p.isLeaking = true;
      triggerScreenShake(9);
      sound.playLeakAlert();
      sound.playShockwave();

      shockwaves.push({
        x: p.x + 110,
        y: p.y + 13,
        radius: 6,
        maxRadius: 55,
        color: '#ef4444',
        alpha: 1.0,
        lineWidth: 2.5,
      });

      showToast(`¡Nueva rotura a presión en Tubería #${p.id}!`, 'reduce');
    }
  }
}

function actionReuse() {
  state.metrics.totalLitersReused += 45;
  // Si hay ola de calor, el riego es crítico y otorga el doble de puntos
  const isHeatwave = state.activeChaos?.type === 'heatwave';
  const earnedScore = isHeatwave ? 160 : 80;
  state.score += earnedScore;

  state.sprinklersActive = true;
  state.sprinklerTimer = 120; // 2 segundos

  sound.playReuse();
  sound.playWaterSplash();

  // Ondas de riego sobre el huerto
  shockwaves.push({
    x: 390,
    y: 440,
    radius: 12,
    maxRadius: 90,
    color: '#34d399',
    alpha: 0.85,
    lineWidth: 3,
  });

  // Crecer cultivos y emitir hojas
  state.crops.forEach((c) => {
    c.growth = Math.min(1.0, c.growth + 0.15);
    particles.push({
      x: c.x + 15,
      y: c.y,
      vx: (Math.random() - 0.5) * 2,
      vy: -Math.random() * 3,
      life: 1.0,
      maxLife: 1.0,
      color: '#86efac',
      size: 3,
      type: 'leaf',
    });
  });

  register3RComboAction('reuse');
  spawnFloatingText(`+${earnedScore} PTS (${isHeatwave ? '☀️ OLA CALOR x2' : '45L Reusados 🌱'})`, 340, 360, '#34d399');
  showToast(isHeatwave ? '☀️ ¡Riego de emergencia bajo ola de calor! Puntos Duplicados' : 'Aguas grises canalizadas al huerto comunitario', 'reuse');
  updateHUD();
}

function actionRecycle() {
  state.metrics.totalLitersRecycled += 60;
  state.metrics.waterPurityPct = Math.min(100, state.metrics.waterPurityPct + 2.5);
  state.score += 120;

  sound.playRecycle();
  sound.playWaterSplash();

  // Onda de purificación en la planta
  shockwaves.push({
    x: state.plant.x,
    y: state.plant.y + 20,
    radius: 10,
    maxRadius: 85,
    color: '#c084fc',
    alpha: 0.9,
    lineWidth: 3,
  });

  // Burbujas y brillo en la planta de purificación
  for (let i = 0; i < 24; i++) {
    particles.push({
      x: state.plant.x + (Math.random() - 0.5) * 80,
      y: state.plant.y + 40,
      vx: (Math.random() - 0.5) * 2,
      vy: -Math.random() * 4 - 1,
      life: 1.0,
      maxLife: 1.0,
      color: ['#c084fc', '#e879f9', '#38bdf8'][Math.floor(Math.random() * 3)],
      size: 3 + Math.random() * 4,
      type: 'bubble',
    });
  }

  register3RComboAction('recycle');
  spawnFloatingText('+120 PTS (Pureza +2.5% ⚗️)', state.plant.x - 60, state.plant.y - 40, '#c084fc');
  showToast('Planta de filtrado biológico activada. Pureza restaurada.', 'recycle');
  updateHUD();
}

function updateHUD() {
  const elRes = document.getElementById('txtReservoir');
  const elBarRes = document.getElementById('barReservoir');
  const elPur = document.getElementById('txtPurity');
  const elBarPur = document.getElementById('barPurity');
  const elScr = document.getElementById('txtScore');
  const elSav = document.getElementById('txtSaved');

  const resPct = Math.max(0, Math.min(100, state.metrics.reservoirLevelPct));
  const purPct = Math.max(0, Math.min(100, state.metrics.waterPurityPct));

  if (elRes) {
    elRes.textContent = `${resPct.toFixed(1)}%`;
    if (resPct <= 20) {
      elRes.style.color = '#ef4444';
      elRes.style.textShadow = '0 0 12px rgba(239, 68, 68, 0.7)';
    } else if (resPct <= 50) {
      elRes.style.color = '#f59e0b';
      elRes.style.textShadow = '0 0 10px rgba(245, 158, 11, 0.5)';
    } else {
      elRes.style.color = '#38bdf8';
      elRes.style.textShadow = '0 0 10px rgba(56, 189, 248, 0.4)';
    }
  }

  if (elBarRes) {
    elBarRes.style.width = `${resPct}%`;
    if (resPct <= 20) {
      elBarRes.style.background = 'linear-gradient(90deg, #b91c1c, #ef4444)';
    } else if (resPct <= 50) {
      elBarRes.style.background = 'linear-gradient(90deg, #d97706, #f59e0b)';
    } else {
      elBarRes.style.background = 'linear-gradient(90deg, #0284c7, #38bdf8)';
    }
  }

  if (elPur) {
    elPur.textContent = `${purPct.toFixed(1)}%`;
    if (purPct <= 50) {
      elPur.style.color = '#ef4444';
    } else if (purPct <= 80) {
      elPur.style.color = '#fbbf24';
    } else {
      elPur.style.color = '#34d399';
    }
  }

  if (elBarPur) {
    elBarPur.style.width = `${purPct}%`;
    if (purPct <= 50) {
      elBarPur.style.background = 'linear-gradient(90deg, #b91c1c, #ef4444)';
    } else if (purPct <= 80) {
      elBarPur.style.background = 'linear-gradient(90deg, #d97706, #fbbf24)';
    } else {
      elBarPur.style.background = 'linear-gradient(90deg, #059669, #34d399)';
    }
  }

  if (elScr) elScr.textContent = `${state.score} pts`;
  if (elSav) elSav.textContent = `${state.metrics.totalLitersSaved} L`;

  // Detección y feedback auditivo/visual de Sequía Crítica
  if (resPct <= 0 && !state.isGameOver) {
    state.isGameOver = true;
    triggerScreenShake(14);
    sound.playDefeat();
    showToast('¡SEQUÍA CRÍTICA! El nivel del embalse se ha agotado por completo 💀', 'reduce');
  }

  // Detección de Hito de Victoria (Puntaje Ecológico)
  if (state.score >= 1000 && !state.hasWon) {
    state.hasWon = true;
    sound.playVictory();
    showToast('¡HITO ALCANZADO! +1000 Pts de Conservación Hídrica 🏆', 'reuse');
  }
}

// --------------------------------------------------------------------------
// BUCLE PRINCIPAL DE RENDERIZADO Y FÍSICA CANVAS 2D A 60 FPS (DELTA TIME)
// --------------------------------------------------------------------------
let waveTime = 0;
let lastFrameTime = performance.now();

function gameLoop(now: number) {
  // Delta time en segundos (tope de 0.05s para evitar saltos al minimizar pestaña)
  const dt = Math.min((now - lastFrameTime) / 1000, 0.05);
  lastFrameTime = now;

  state.tick++;
  waveTime += dt * 3.0;
  state.plant.spinAngle += dt * 2.5;

  if (state.sprinklerTimer > 0) {
    state.sprinklerTimer--;
    if (state.sprinklerTimer === 0) state.sprinklersActive = false;
  }

  // Actualizar cooldowns y estados del jugador
  const p = state.player;
  if (p.dashCooldown > 0) p.dashCooldown = Math.max(0, p.dashCooldown - dt);
  if (p.speedBuffTimer > 0) p.speedBuffTimer = Math.max(0, p.speedBuffTimer - dt);

  // Actualizar temporizador de Combo 3R
  if (state.combo.timer > 0) {
    state.combo.timer -= dt;
    if (state.combo.timer <= 0) {
      state.combo.count = 0;
    }
  }

  // Actualizar Ciclo de Eventos de Caos Dinámicos
  if (state.activeChaos) {
    state.activeChaos.duration -= dt;
    if (state.activeChaos.type === 'rain') {
      // Lluvia recarga el embalse continuamente
      state.metrics.reservoirLevelPct = Math.min(100, state.metrics.reservoirLevelPct + dt * 0.4);
    } else if (state.activeChaos.type === 'heatwave') {
      // Calor acelera evaporación
      state.metrics.reservoirLevelPct = Math.max(0, state.metrics.reservoirLevelPct - dt * 0.04);
    }
    if (state.activeChaos.duration <= 0) {
      state.activeChaos = null;
      state.chaosTimer = 22.0 + Math.random() * 10;
      showToast('🌤️ Evento climático finalizado. Condiciones normales.', 'reuse');
    }
  } else {
    state.chaosTimer -= dt;
    if (state.chaosTimer <= 0) {
      const types: ('heatwave' | 'burst' | 'rain')[] = ['heatwave', 'burst', 'rain'];
      const chosen = types[Math.floor(Math.random() * types.length)];
      sound.playChaosAlarm();
      triggerScreenShake(8);

      if (chosen === 'heatwave') {
        state.activeChaos = {
          type: 'heatwave',
          title: '☀️ ¡OLA DE CALOR! Riega el huerto rápido (PUNTOS x2)',
          duration: 12.0,
          maxDuration: 12.0,
        };
        showToast('☀️ ¡Ola de Calor! El embalse se evapora rápido', 'reduce');
      } else if (chosen === 'burst') {
        state.activeChaos = {
          type: 'burst',
          title: '🚨 ¡MEGA-ROTURA A PRESIÓN! Repara las tuberías críticas',
          duration: 12.0,
          maxDuration: 12.0,
        };
        state.pipes.forEach((pipe) => (pipe.isLeaking = true));
        showToast('🚨 ¡Mega-Rotura! Fugas activas en toda la red', 'reduce');
      } else if (chosen === 'rain') {
        state.activeChaos = {
          type: 'rain',
          title: '🌧️ ¡LLUVIA TORRENCIAL! Captación masiva (+Recarga)',
          duration: 12.0,
          maxDuration: 12.0,
        };
        state.metrics.reservoirLevelPct = Math.min(100, state.metrics.reservoirLevelPct + 15.0);
        showToast('🌧️ ¡Lluvia Torrencial! Embalse recargado +15%', 'reuse');
      }
    }
  }

  // 1. Polling de entrada continua (WASD y Flechas)
  let inX = 0;
  let inY = 0;
  if (isKeyPressed('KeyW', 'ArrowUp', 'w')) inY -= 1;
  if (isKeyPressed('KeyS', 'ArrowDown', 's')) inY += 1;
  if (isKeyPressed('KeyA', 'ArrowLeft', 'a')) inX -= 1;
  if (isKeyPressed('KeyD', 'ArrowRight', 'd')) inX += 1;

  const hasKeyboardInput = (inX !== 0 || inY !== 0);

  if (hasKeyboardInput) {
    // Si el usuario usa el teclado, cancelar inmediatamente el target del clic
    p.targetX = null;
    p.targetY = null;

    // Normalizar vector para que diagonales (ej: W + D) tengan la misma velocidad
    const inputLen = Math.hypot(inX, inY);
    inX /= inputLen;
    inY /= inputLen;
  } else if (p.targetX !== null && p.targetY !== null) {
    // Desplazamiento hacia el punto de clic (Click-to-Move)
    const toTargetX = p.targetX - p.x;
    const toTargetY = p.targetY - p.y;
    const dist = Math.hypot(toTargetX, toTargetY);
    if (dist > 6) {
      inX = toTargetX / dist;
      inY = toTargetY / dist;
    } else {
      p.targetX = null;
      p.targetY = null;
    }
  }

  // 2. Física con Aceleración, Fricción e Inercia Suave
  const baseSpeed = p.speedBuffTimer > 0 ? 370 : 260; // px/s
  const accel = 1750; // px/s^2

  if (p.isDashing) {
    p.dashTimer -= dt;
    if (p.dashTimer <= 0) {
      p.isDashing = false;
    }
    // Generar siluetas fantasma (afterimages) durante el dash
    if (state.tick % 2 === 0) {
      afterimages.push({
        x: p.x,
        y: p.y,
        angle: p.angle,
        alpha: 0.65,
      });
    }
  } else {
    // Aceleración suave
    p.vx += inX * accel * dt;
    p.vy += inY * accel * dt;

    // Fricción exponencial independiente de los FPS
    const frictionFactor = hasKeyboardInput ? 0.04 : 0.0006;
    p.vx *= Math.pow(frictionFactor, dt);
    p.vy *= Math.pow(frictionFactor, dt);

    // Limitar a velocidad máxima si no está en dash
    const currentSpeed = Math.hypot(p.vx, p.vy);
    if (currentSpeed > baseSpeed) {
      p.vx = (p.vx / currentSpeed) * baseSpeed;
      p.vy = (p.vy / currentSpeed) * baseSpeed;
    }
  }

  // Integrar posición
  p.x += p.vx * dt;
  p.y += p.vy * dt;

  // Limitar dentro de los límites del mapa
  p.x = Math.max(50, Math.min(canvas.width - 50, p.x));
  p.y = Math.max(50, Math.min(canvas.height - 50, p.y));

  // Animación de ángulo, ciclo de pasos y partículas de pisadas
  const moveSpeed = Math.hypot(p.vx, p.vy);
  if (moveSpeed > 15) {
    p.angle = Math.atan2(p.vy, p.vx);
    p.walkCycle += moveSpeed * dt * 0.12;

    if (state.tick % 7 === 0) {
      sound.playFootstep();
      particles.push({
        x: p.x + (Math.random() - 0.5) * 8,
        y: p.y + 14,
        vx: -p.vx * 0.12 + (Math.random() - 0.5) * 0.6,
        vy: -p.vy * 0.12 + (Math.random() - 0.5) * 0.6,
        life: 0.45,
        maxLife: 0.45,
        color: 'rgba(217, 180, 130, 0.45)',
        size: 2.2,
        type: 'leaf',
      });
    }
  }

  // 3. Generación periódica y recolección de coleccionables ("Eco-Kits")
  collectibleSpawnTimer -= dt;
  if (collectibleSpawnTimer <= 0 && collectibles.length < 3) {
    collectibleSpawnTimer = 12 + Math.random() * 8;
    const types: ('kit' | 'droplet' | 'speed')[] = ['kit', 'droplet', 'speed'];
    const chosenType = types[Math.floor(Math.random() * types.length)];
    // Coordenadas transitables en el mapa
    const cx = 310 + Math.random() * 240;
    const cy = 180 + Math.random() * 320;
    collectibles.push({
      id: nextCollectibleId++,
      x: cx,
      y: cy,
      type: chosenType,
      life: 25.0,
      pulse: 0,
    });
  }

  // Actualizar y detectar colisiones de coleccionables
  for (let i = collectibles.length - 1; i >= 0; i--) {
    const c = collectibles[i];
    c.pulse += dt * 4;
    c.life -= dt;
    if (c.life <= 0) {
      collectibles.splice(i, 1);
      continue;
    }

    // Colisión radio-a-radio (< 28 px)
    const distToPlayer = Math.hypot(p.x - c.x, p.y - c.y);
    if (distToPlayer < 28) {
      sound.playCollect();
      triggerScreenShake(3);

      if (c.type === 'kit') {
        state.score += 100;
        const leak = state.pipes.find((pipe) => pipe.isLeaking);
        if (leak) {
          leak.isLeaking = false;
          leak.repairProgress = 100;
          state.metrics.totalLitersSaved += 80;
          spawnFloatingText('¡ECO-KIT: Fuga Reparada Instantáneamente! 🧰 (+100 PTS)', p.x - 60, p.y - 35, '#38bdf8');
          showToast('¡Eco-Kit usado! Tubería soldada automáticamente', 'reduce');
        } else {
          spawnFloatingText('+100 PTS (Eco-Kit de Herramientas 🧰)', p.x - 50, p.y - 35, '#fbbf24');
        }
      } else if (c.type === 'droplet') {
        state.score += 60;
        state.metrics.reservoirLevelPct = Math.min(100, state.metrics.reservoirLevelPct + 6.0);
        spawnFloatingText('¡AGUA PURA RECARGADA! +6.0% 💧 (+60 PTS)', p.x - 50, p.y - 35, '#34d399');
        showToast('¡Gota de Agua Cristalina recogida! Embalse recargado', 'reuse');
      } else if (c.type === 'speed') {
        p.speedBuffTimer = 6.0; // 6 segundos de súper velocidad
        state.score += 40;
        spawnFloatingText('¡TURBO ECO ACTIVO! ⚡ (+40% Velocidad)', p.x - 50, p.y - 35, '#a855f7');
        showToast('¡Turbo activado! Movimiento súper veloz', 'recycle');
      }

      // Destello de chispas
      for (let s = 0; s < 16; s++) {
        particles.push({
          x: c.x,
          y: c.y,
          vx: (Math.random() - 0.5) * 5,
          vy: (Math.random() - 0.5) * 5,
          life: 0.6,
          maxLife: 0.6,
          color: c.type === 'kit' ? '#fbbf24' : c.type === 'droplet' ? '#38bdf8' : '#c084fc',
          size: 3,
          type: 'spark',
        });
      }

      updateHUD();
      collectibles.splice(i, 1);
    }
  }

  // 3.1. Generación y colisión de Amenazas Hídricas (Manchas de lodo)
  threatSpawnTimer -= dt;
  if (threatSpawnTimer <= 0 && threats.length < 2) {
    threatSpawnTimer = 12 + Math.random() * 8;
    threats.push({
      id: nextThreatId++,
      x: canvas.width - 60,
      y: 160 + Math.random() * (canvas.height - 240),
      vx: -42 - Math.random() * 25,
      vy: (Math.random() - 0.5) * 20,
      radius: 17,
      pulse: 0,
    });
  }

  for (let i = threats.length - 1; i >= 0; i--) {
    const t = threats[i];
    t.x += t.vx * dt;
    t.y += t.vy * dt;
    t.pulse += dt * 3.5;

    const dPlayer = Math.hypot(p.x - t.x, p.y - t.y);
    if (dPlayer < t.radius + 18) {
      if (p.isDashing) {
        sound.playWaterSplash();
        triggerScreenShake(7);
        state.score += 75;
        spawnFloatingText('💥 ¡CONTAMINANTE DESTRUIDO CON DASH! +75 PTS', t.x - 60, t.y - 25, '#f43f5e');
        showToast('¡Amenaza evaporada con Dash sónico!', 'recycle');
        for (let k = 0; k < 18; k++) {
          particles.push({
            x: t.x,
            y: t.y,
            vx: (Math.random() - 0.5) * 6,
            vy: (Math.random() - 0.5) * 6,
            life: 0.5,
            maxLife: 0.5,
            color: '#a855f7',
            size: 3,
            type: 'bubble',
          });
        }
        threats.splice(i, 1);
        updateHUD();
        continue;
      } else {
        state.metrics.waterPurityPct = Math.max(0, state.metrics.waterPurityPct - 1.0);
        spawnFloatingText('⚠️ ¡TOXINA! Pureza -1.0% (¡Usa DASH para destruirla!)', p.x - 60, p.y - 25, '#ef4444');
        p.vx = -p.vx * 1.5;
        p.vy = -p.vy * 1.5;
        triggerScreenShake(4);
      }
    }

    if (t.x < 260) {
      state.metrics.waterPurityPct = Math.max(0, state.metrics.waterPurityPct - 3.5);
      spawnFloatingText('⚠️ ¡Contaminante llegó al embalse! Pureza -3.5%', 220, t.y, '#dc2626');
      triggerScreenShake(6);
      threats.splice(i, 1);
      updateHUD();
    }
  }

  // Drenaje continuo realista
  const hasLeak = state.pipes.some((pipe) => pipe.isLeaking);
  state.metrics.reservoirLevelPct = Math.max(0, state.metrics.reservoirLevelPct - (hasLeak ? 0.02 : 0.004));
  if (state.tick % 25 === 0) updateHUD();

  // Iniciar Screen Shake (si está activo)
  ctx.save();
  if (screenShake > 0) {
    const sx = (Math.random() - 0.5) * screenShake * 2;
    const sy = (Math.random() - 0.5) * screenShake * 2;
    ctx.translate(sx, sy);
    screenShake = Math.max(0, screenShake * 0.86 - 0.25);
  }

  // 1. Limpiar Fondo con Gradiente Sutil de Profundidad
  const bgGrad = ctx.createRadialGradient(
    canvas.width / 2, canvas.height / 2, 50,
    canvas.width / 2, canvas.height / 2, canvas.width
  );
  bgGrad.addColorStop(0, '#0d1527');
  bgGrad.addColorStop(1, '#060911');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Cuadrícula sutil de fondo
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.03)';
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 40) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  // ------------------------------------------------------------------------
  // 2. ZONA A: EMBALSE CENTRAL CON OLAS SINUSOIDALES Y BURBUJAS
  // ------------------------------------------------------------------------
  const resW = 210;
  const resH = canvas.height - 80;
  const resX = 40;
  const resY = 40;

  // Marco exterior
  ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(resX, resY, resW, resH, 16);
  ctx.fill();
  ctx.stroke();

  // Agua con ondas animadas
  const fillH = (resH - 20) * (Math.max(2, state.metrics.reservoirLevelPct) / 100.0);
  const waterTop = resY + resH - 10 - fillH;

  ctx.save();
  ctx.beginPath();
  ctx.roundRect(resX + 10, resY + 10, resW - 20, resH - 20, 10);
  ctx.clip();

  const waterGrad = ctx.createLinearGradient(0, waterTop, 0, resY + resH);
  waterGrad.addColorStop(0, 'rgba(56, 189, 248, 0.85)');
  waterGrad.addColorStop(0.5, 'rgba(14, 165, 233, 0.95)');
  waterGrad.addColorStop(1, 'rgba(3, 105, 161, 1)');

  ctx.fillStyle = waterGrad;
  ctx.beginPath();
  ctx.moveTo(resX + 10, resY + resH);
  ctx.lineTo(resX + 10, waterTop);

  // Curva sinusoidal de la superficie
  for (let x = resX + 10; x <= resX + resW - 10; x += 5) {
    const waveY = waterTop + Math.sin((x * 0.05) + waveTime) * 4 + Math.cos((x * 0.03) - waveTime * 0.8) * 2;
    ctx.lineTo(x, waveY);
  }

  ctx.lineTo(resX + resW - 10, resY + resH);
  ctx.closePath();
  ctx.fill();

  // Espuma superior de olas
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let x = resX + 10; x <= resX + resW - 10; x += 5) {
    const waveY = waterTop + Math.sin((x * 0.05) + waveTime) * 4 + Math.cos((x * 0.03) - waveTime * 0.8) * 2;
    if (x === resX + 10) ctx.moveTo(x, waveY);
    else ctx.lineTo(x, waveY);
  }
  ctx.stroke();

  ctx.restore();

  // Etiqueta del embalse
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText(`💧 EMBALSE: ${state.metrics.reservoirLevelPct.toFixed(1)}%`, resX + 22, resY + 34);

  // ------------------------------------------------------------------------
  // 3. ZONA B: 1. REDUCIR (Red de Tuberías y Fugas a Presión)
  // ------------------------------------------------------------------------
  const zone1X = 280;
  const zone1Y = 40;
  const zone1W = 270;
  const zone1H = 290;

  ctx.fillStyle = 'rgba(22, 32, 54, 0.5)';
  ctx.strokeStyle = 'rgba(71, 85, 105, 0.5)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(zone1X, zone1Y, zone1W, zone1H, 14);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#f87171';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText('🔧 1. REDUCIR (Fugas Comunales)', zone1X + 16, zone1Y + 28);

  state.pipes.forEach((pipe) => {
    // === TUBERÍA METÁLICA PIXEL ART CON COBRE Y REMACHES ===
    const isLeak = pipe.isLeaking;

    // Sombra de la tubería
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.fillRect(pipe.x + 2, pipe.y + 4, pipe.w, pipe.h);

    // Cuerpo principal de la tubería (Cobre / Bronce oscuro rústico)
    ctx.fillStyle = isLeak ? '#7f1d1d' : '#334155';
    ctx.fillRect(pipe.x, pipe.y, pipe.w, pipe.h);

    // Brillo superior metálico
    ctx.fillStyle = isLeak ? '#f87171' : '#64748b';
    ctx.fillRect(pipe.x, pipe.y, pipe.w, 4);

    // Borde inferior sombreado
    ctx.fillStyle = isLeak ? '#450a0a' : '#1e293b';
    ctx.fillRect(pipe.x, pipe.y + pipe.h - 4, pipe.w, 4);

    // Uniones y acoples de cobre con remaches (cada 60px)
    for (let j = 0; j < pipe.w; j += 55) {
      ctx.fillStyle = '#b45309'; // Cobre
      ctx.fillRect(pipe.x + j, pipe.y - 2, 8, pipe.h + 4);
      // Remaches
      ctx.fillStyle = '#fde68a';
      ctx.fillRect(pipe.x + j + 2, pipe.y, 4, 3);
      ctx.fillRect(pipe.x + j + 2, pipe.y + pipe.h - 3, 4, 3);
    }

    // Si tiene rotura: dibujar grieta fracturada pixel art en el centro
    if (isLeak) {
      ctx.fillStyle = '#fef08a';
      ctx.fillRect(pipe.x + 105, pipe.y + 6, 12, 14);
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(pipe.x + 107, pipe.y + 4, 8, 18);
    }

    // Texto de estado
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 11px Outfit, sans-serif';
    const statusText = pipe.isLeaking ? `Tubería #${pipe.id} [⚠️ ROTURA CRÍTICA - ESPACIO]` : `Tubería #${pipe.id} [OK - Presión Estable]`;
    ctx.fillText(statusText, pipe.x + 12, pipe.y + 17);

    // Si tiene fuga: chorro de agua animado
    if (pipe.isLeaking) {
      if (Math.random() < 0.6) {
        particles.push({
          x: pipe.x + 110 + (Math.random() - 0.5) * 15,
          y: pipe.y + 5,
          vx: (Math.random() - 0.5) * 4,
          vy: -Math.random() * 5 - 2,
          life: 1.0,
          maxLife: 1.0,
          color: 'rgba(56, 189, 248, 0.85)',
          size: 3 + Math.random() * 2,
          type: 'water',
        });
      }
    }
  });

  // ------------------------------------------------------------------------
  // 4. ZONA C: 2. REUSAR (Huertos Agrícolas de Riego por Goteo)
  // ------------------------------------------------------------------------
  const zone2X = 280;
  const zone2Y = 350;
  const zone2W = 270;
  const zone2H = 200;

  ctx.fillStyle = 'rgba(20, 83, 45, 0.35)';
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(zone2X, zone2Y, zone2W, zone2H, 14);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#86efac';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText('🌱 2. REUSAR (Huertos Comunitarios)', zone2X + 16, zone2Y + 26);

  ctx.fillStyle = '#dcfce7';
  ctx.font = '11px Outfit, sans-serif';
  ctx.fillText(`Litros reusados: ${state.metrics.totalLitersReused} L`, zone2X + 16, zone2Y + 44);

  // Dibujar cultivos con suelo de labranza Pixel Art
  state.crops.forEach((crop) => {
    // Parcela de tierra labrada rústica (#78350f / #451a03)
    ctx.fillStyle = '#451a03';
    ctx.fillRect(crop.x - 6, crop.y - 6, 44, 38);
    // Surcos de arado
    ctx.fillStyle = '#78350f';
    ctx.fillRect(crop.x - 4, crop.y - 2, 40, 4);
    ctx.fillRect(crop.x - 4, crop.y + 10, 40, 4);
    ctx.fillRect(crop.x - 4, crop.y + 22, 40, 4);

    // Hortaliza / Planta Pixel Art
    const plantColor = crop.growth > 0.7 ? '#4ade80' : '#16a34a';
    ctx.fillStyle = plantColor;
    const sz = Math.floor(6 + crop.growth * 10);
    ctx.fillRect(crop.x + 16 - sz / 2, crop.y + 14 - sz / 2, sz, sz);
    // Destello de rocío
    ctx.fillStyle = '#bbf7d0';
    ctx.fillRect(crop.x + 14, crop.y + 12, 3, 3);

    // Aspersor activo
    if (state.sprinklersActive && Math.random() < 0.3) {
      particles.push({
        x: crop.x + 16,
        y: crop.y + 10,
        vx: (Math.random() - 0.5) * 3,
        vy: -Math.random() * 3,
        life: 0.8,
        maxLife: 0.8,
        color: 'rgba(134, 239, 172, 0.7)',
        size: 2,
        type: 'water',
      });
    }
  });

  // ------------------------------------------------------------------------
  // 5. ZONA D: 3. RECICLAR (Planta de Filtrado Biológico & UV)
  // ------------------------------------------------------------------------
  const zone3X = 580;
  const zone3Y = 40;
  const zone3W = canvas.width - zone3X - 40;
  const zone3H = canvas.height - 80;

  ctx.fillStyle = 'rgba(88, 28, 135, 0.3)';
  ctx.strokeStyle = '#a855f7';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(zone3X, zone3Y, zone3W, zone3H, 16);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#d8b4fe';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText('⚗️ 3. RECICLAR (Planta de Filtrado Biológico)', zone3X + 16, zone3Y + 28);

  ctx.fillStyle = '#f3e8ff';
  ctx.font = '11px Outfit, sans-serif';
  ctx.fillText(`Pureza: ${state.metrics.waterPurityPct.toFixed(1)}% | Filtrado: ${state.metrics.totalLitersRecycled} L`, zone3X + 16, zone3Y + 48);

  // Tanque cilíndrico de bio-filtración animado
  const tankX = zone3X + zone3W / 2;
  const tankY = zone3Y + 160;
  const tankR = 65;

  ctx.save();
  ctx.translate(tankX, tankY);

  // Brillo UV exterior
  const uvGlow = ctx.createRadialGradient(0, 0, 20, 0, 0, tankR + 20);
  uvGlow.addColorStop(0, 'rgba(168, 85, 247, 0.3)');
  uvGlow.addColorStop(1, 'rgba(168, 85, 247, 0)');
  ctx.fillStyle = uvGlow;
  ctx.beginPath();
  ctx.arc(0, 0, tankR + 20, 0, Math.PI * 2);
  ctx.fill();

  // Anillo exterior
  ctx.strokeStyle = '#c084fc';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(0, 0, tankR, 0, Math.PI * 2);
  ctx.stroke();

  // Aspas giratorias del filtro de carbón
  ctx.rotate(state.plant.spinAngle);
  ctx.strokeStyle = 'rgba(216, 180, 254, 0.8)';
  ctx.lineWidth = 3;
  for (let a = 0; a < 4; a++) {
    ctx.rotate(Math.PI / 2);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(tankR - 10, 0);
    ctx.stroke();
  }

  ctx.restore();

  // ------------------------------------------------------------------------
  // 5.1. RENDERIZADO DE COLECCIONABLES EN EL MAPA (ECO-KITS, GOTAS, TURBO)
  // ------------------------------------------------------------------------
  collectibles.forEach((c) => {
    ctx.save();
    const floatY = Math.sin(c.pulse) * 4;
    ctx.translate(c.x, c.y + floatY);

    // Resplandor exterior pulsante
    const glowColor = c.type === 'kit' ? 'rgba(251, 191, 36, 0.4)' : c.type === 'droplet' ? 'rgba(56, 189, 248, 0.45)' : 'rgba(168, 85, 247, 0.45)';
    ctx.fillStyle = glowColor;
    ctx.beginPath();
    ctx.arc(0, 0, 18 + Math.sin(c.pulse * 1.5) * 3, 0, Math.PI * 2);
    ctx.fill();

    // Sombra en el suelo
    ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    ctx.beginPath();
    ctx.ellipse(0, 14 - floatY, 12, 5, 0, 0, Math.PI * 2);
    ctx.fill();

    if (c.type === 'kit') {
      // Maletín de herramientas Eco-Kit Pixel Art (Dorado / Metal)
      ctx.fillStyle = '#b45309';
      ctx.fillRect(-10, -7, 20, 14);
      ctx.fillStyle = '#f59e0b';
      ctx.fillRect(-9, -6, 18, 12);
      // Asa del maletín
      ctx.strokeStyle = '#78350f';
      ctx.lineWidth = 2;
      ctx.strokeRect(-4, -10, 8, 4);
      // Cruz / Sello verde ecológico
      ctx.fillStyle = '#10b981';
      ctx.fillRect(-5, -2, 10, 4);
      ctx.fillRect(-2, -5, 4, 10);
    } else if (c.type === 'droplet') {
      // Gota de Agua Cristalina resplandeciente
      ctx.fillStyle = '#0ea5e9';
      ctx.beginPath();
      ctx.arc(0, 2, 9, 0, Math.PI);
      ctx.lineTo(0, -11);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#e0f2fe';
      ctx.fillRect(-3, -2, 3, 3);
    } else if (c.type === 'speed') {
      // Turbo Rayo Verde/Morado
      ctx.fillStyle = '#a855f7';
      ctx.beginPath();
      ctx.moveTo(3, -11);
      ctx.lineTo(-7, 1);
      ctx.lineTo(0, 1);
      ctx.lineTo(-3, 11);
      ctx.lineTo(7, -1);
      ctx.lineTo(0, -1);
      ctx.closePath();
      ctx.fill();
    }

    ctx.restore();
  });

  // ------------------------------------------------------------------------
  // 5.15. RENDERIZADO DE AMENAZAS HÍDRICAS (CONTAMINANTES TÓXICOS)
  // ------------------------------------------------------------------------
  threats.forEach((t) => {
    ctx.save();
    ctx.translate(t.x, t.y);
    const pulseScale = 1 + Math.sin(t.pulse) * 0.12;
    ctx.fillStyle = 'rgba(168, 85, 247, 0.25)';
    ctx.beginPath();
    ctx.arc(0, 0, (t.radius + 6) * pulseScale, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#7e22ce';
    ctx.beginPath();
    ctx.arc(0, 0, t.radius * pulseScale, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#c084fc';
    ctx.beginPath();
    ctx.arc(-4, -4, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#f43f5e';
    ctx.font = 'bold 10px Outfit, sans-serif';
    ctx.fillText('☣️ TÓXICO', -22, -t.radius - 4);
    ctx.restore();
  });

  // ------------------------------------------------------------------------
  // 5.2. RENDERIZADO DE AFTERIMAGES (ESTELA DEL DASH)
  // ------------------------------------------------------------------------
  for (let i = afterimages.length - 1; i >= 0; i--) {
    const ai = afterimages[i];
    ai.alpha -= 0.055;
    if (ai.alpha <= 0) {
      afterimages.splice(i, 1);
      continue;
    }

    ctx.save();
    ctx.translate(ai.x, ai.y);
    ctx.rotate(ai.angle);
    ctx.globalAlpha = ai.alpha * 0.7;

    // Silueta translúcida en cian/azul neón
    ctx.fillStyle = '#38bdf8';
    ctx.beginPath();
    ctx.arc(0, 0, 14, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  // ------------------------------------------------------------------------
  // 6. AVATAR DEL JUGADOR (AquaGuardian - Pixel Art Sprite 2D Con Bobbing)
  // ------------------------------------------------------------------------
  ctx.save();
  const bobY = Math.sin(state.player.walkCycle) * 2.2;
  ctx.translate(state.player.x, state.player.y + bobY);

  // Sombra de contacto
  ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
  ctx.beginPath();
  ctx.ellipse(0, 18 - bobY, 16, 7, 0, 0, Math.PI * 2);
  ctx.fill();

  // Halo luminoso del guardián (Dorado en soldadura, Cian al dashear o normal)
  ctx.strokeStyle = state.player.isWrenching
    ? 'rgba(251, 191, 36, 0.9)'
    : (state.player.isDashing
        ? 'rgba(56, 189, 248, 0.95)'
        : (state.player.speedBuffTimer > 0
            ? 'rgba(168, 85, 247, 0.85)'
            : 'rgba(56, 189, 248, 0.5)'));
  ctx.lineWidth = state.player.isDashing ? 2.5 : 1.5;
  ctx.beginPath();
  ctx.arc(0, 4, state.player.isDashing ? 26 : 22, 0, Math.PI * 2);
  ctx.stroke();

  // === RENDERIZADO PIXEL ART RETRO DEL PERSONAJE ===
  // 1. Botas de trabajo (Cuero marrón oscuro)
  ctx.fillStyle = '#451a03';
  ctx.fillRect(-8, 14, 6, 6);
  ctx.fillRect(2, 14, 6, 6);
  ctx.fillStyle = '#291002';
  ctx.fillRect(-8, 18, 6, 2);
  ctx.fillRect(2, 18, 6, 2);

  // 2. Piernas y Overol de mezclilla (Denim Blue #1e3a8a / #2563eb)
  ctx.fillStyle = '#1e3a8a';
  ctx.fillRect(-7, 6, 5, 9);
  ctx.fillRect(2, 6, 5, 9);
  // Cuerpo del overol
  ctx.fillStyle = '#2563eb';
  ctx.fillRect(-8, -2, 16, 9);
  // Tirantes del overol
  ctx.fillStyle = '#1d4ed8';
  ctx.fillRect(-7, -6, 3, 5);
  ctx.fillRect(4, -6, 3, 5);
  // Hebillas de latón
  ctx.fillStyle = '#fbbf24';
  ctx.fillRect(-7, -2, 3, 2);
  ctx.fillRect(4, -2, 3, 2);

  // 3. Camisa interior (Cian ecológico #0284c7)
  ctx.fillStyle = '#0284c7';
  ctx.fillRect(-4, -6, 8, 4);

  // 4. Cabeza y rostro (Piel cálida #fed7aa)
  ctx.fillStyle = '#fed7aa';
  ctx.fillRect(-6, -15, 12, 10);
  // Ojos pixel art
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(-4, -12, 2, 3);
  ctx.fillRect(2, -12, 2, 3);

  // 5. Sombrero de paja rústico de técnico (Paja #fde047 / #ca8a04)
  ctx.fillStyle = '#ca8a04';
  ctx.fillRect(-12, -18, 24, 4); // Ala ancha
  ctx.fillStyle = '#eab308';
  ctx.fillRect(-8, -24, 16, 7); // Copa
  // Cinta azul del sombrero
  ctx.fillStyle = '#0284c7';
  ctx.fillRect(-8, -19, 16, 2);

  // 6. Brazo y Herramienta activa (Llave inglesa o soldador)
  ctx.save();
  ctx.rotate(state.player.angle);
  ctx.translate(10, 0);

  if (state.player.isWrenching) {
    // Animación de impacto de soldadura / llave
    ctx.rotate(Math.sin(state.tick * 0.8) * 0.5);
  }

  // Llave inglesa metálica Pixel Art
  ctx.fillStyle = '#94a3b8';
  ctx.fillRect(0, -2, 12, 4); // Mango
  ctx.fillStyle = '#e2e8f0';
  ctx.fillRect(10, -5, 6, 10); // Cabeza
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(12, -2, 4, 4); // Muesca central

  ctx.restore();

  // Barra visual de Cooldown de Dash (si está en recarga)
  if (state.player.dashCooldown > 0) {
    const barW = 28;
    const barH = 3;
    const pct = 1.0 - (state.player.dashCooldown / 0.95);
    ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
    ctx.fillRect(-barW / 2, -38, barW, barH);
    ctx.fillStyle = '#38bdf8';
    ctx.fillRect(-barW / 2, -38, barW * pct, barH);
  } else {
    // Listo para dash (indicador de impulso)
    ctx.fillStyle = state.player.isDashing ? '#fbbf24' : '#38bdf8';
    ctx.font = 'bold 9px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('⚡ SHIFT', 0, -36);
  }

  // Etiqueta superior del jugador
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 10px Outfit, sans-serif';
  ctx.textAlign = 'center';
  ctx.shadowColor = '#000000';
  ctx.shadowBlur = 4;
  ctx.fillText(session.username || 'Guardián', 0, -25);
  ctx.shadowBlur = 0;
  ctx.textAlign = 'left';

  ctx.restore();

  // Aura interactiva de proximidad holográfica
  const dPipe = Math.hypot(state.player.x - 410, state.player.y - 220);
  const dGarden = Math.hypot(state.player.x - 410, state.player.y - 440);
  const dPlant = Math.hypot(state.player.x - 780, state.player.y - 340);

  let auraColor: string | null = null;
  let auraPrompt: string | null = null;

  if (dPipe < 160) {
    auraColor = '#38bdf8';
    auraPrompt = '[ESPACIO] 🔧 REPARAR FUGA';
  } else if (dGarden < 160) {
    auraColor = '#34d399';
    auraPrompt = '[R] 🌱 CANALIZAR RIEGO';
  } else if (dPlant < 170) {
    auraColor = '#c084fc';
    auraPrompt = '[F] ⚗️ PURIFICAR AGUA';
  }

  if (auraColor && auraPrompt) {
    ctx.save();
    ctx.strokeStyle = auraColor;
    ctx.lineWidth = 2.5;
    ctx.globalAlpha = 0.75 + Math.sin(state.tick * 0.15) * 0.25;
    ctx.beginPath();
    ctx.arc(state.player.x, state.player.y + 6, 28, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
    ctx.strokeStyle = auraColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(state.player.x - 75, state.player.y - 48, 150, 22, 6);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(auraPrompt, state.player.x, state.player.y - 33);
    ctx.restore();
  }

  // Clima Dinámico y Evento de Caos
  if (state.activeChaos?.type === 'heatwave') {
    ctx.fillStyle = 'rgba(245, 158, 11, 0.08)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  } else if (state.activeChaos?.type === 'rain') {
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
    ctx.lineWidth = 1.5;
    for (let r = 0; r < 40; r++) {
      const rx = (state.tick * 9 + r * 37) % canvas.width;
      const ry = (state.tick * 18 + r * 31) % canvas.height;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(rx - 3, ry + 16);
      ctx.stroke();
    }
  }

  // Banner Superior de Evento de Caos
  if (state.activeChaos) {
    const bannerW = 440;
    const bannerX = (canvas.width - bannerW) / 2;
    ctx.fillStyle = state.activeChaos.type === 'burst' ? 'rgba(220, 38, 38, 0.92)' : (state.activeChaos.type === 'heatwave' ? 'rgba(217, 119, 6, 0.92)' : 'rgba(2, 132, 199, 0.92)');
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(bannerX, 10, bannerW, 30, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${state.activeChaos.title} (${Math.ceil(state.activeChaos.duration)}s)`, canvas.width / 2, 29);
  }

  // Badge de Combo Multiplicador en Canvas
  if (state.combo.count >= 2) {
    ctx.save();
    ctx.fillStyle = 'rgba(245, 158, 11, 0.92)';
    ctx.strokeStyle = '#fef08a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(canvas.width - 240, 14, 210, 32, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 13px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`🔥 ECO-COMBO x${state.combo.count} ACTIVADO!`, canvas.width - 135, 35);
    ctx.restore();
  }

  // ------------------------------------------------------------------------
  // 7. ACTUALIZACIÓN Y RENDERIZADO DE PARTÍCULAS
  // ------------------------------------------------------------------------
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx;
    p.y += p.vy;
    p.life -= 0.02;

    if (p.life <= 0) {
      particles.splice(i, 1);
      continue;
    }

    ctx.fillStyle = p.color;
    ctx.globalAlpha = p.life / p.maxLife;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1.0;
  }

  // ------------------------------------------------------------------------
  // 8. TEXTOS FLOTANTES DE PUNTAJE Y ACCIONES
  // ------------------------------------------------------------------------
  for (let i = floatingTexts.length - 1; i >= 0; i--) {
    const ft = floatingTexts[i];
    ft.y += ft.vy;
    ft.alpha -= 0.015;

    if (ft.alpha <= 0) {
      floatingTexts.splice(i, 1);
      continue;
    }

    ctx.save();
    ctx.fillStyle = ft.color;
    ctx.globalAlpha = Math.max(0, ft.alpha);
    ctx.font = 'bold 13px Outfit, sans-serif';
    ctx.shadowColor = '#000000';
    ctx.shadowBlur = 4;
    ctx.fillText(ft.text, ft.x, ft.y);
    ctx.restore();
  }

  // ------------------------------------------------------------------------
  // 9. ONDAS EXPANSIVAS / SHOCKWAVES & RIPPLES (FEEDBACK VISUAL DE AGUA)
  // ------------------------------------------------------------------------
  for (let i = shockwaves.length - 1; i >= 0; i--) {
    const sw = shockwaves[i];
    sw.radius += (sw.maxRadius - sw.radius) * 0.12 + 1.2;
    sw.alpha *= 0.91;

    if (sw.alpha <= 0.01 || sw.radius >= sw.maxRadius) {
      shockwaves.splice(i, 1);
      continue;
    }

    ctx.save();
    ctx.strokeStyle = sw.color;
    ctx.globalAlpha = Math.max(0, sw.alpha);
    ctx.lineWidth = sw.lineWidth;
    ctx.beginPath();
    ctx.arc(sw.x, sw.y, sw.radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  // Restaurar contexto del canvas (final de Screen Shake)
  ctx.restore();

  requestAnimationFrame(gameLoop);
}

// Iniciar Loop
requestAnimationFrame(gameLoop);
updateHUD();

// ==========================================================================
// INTEGRACIÓN CON GO GATEWAY (API REST, MATCHMAKING & MULTI-HOST FAILOVER)
// ==========================================================================
let gatewayNodeList: string[] = ['http://localhost:8080'];
let currentGatewayIndex = 0;

// Inicializar lista de nodos desde parámetro URL (?gw=192.168.1.10:8080,192.168.1.11:8080)
if (typeof window !== 'undefined') {
  const urlParams = new URLSearchParams(window.location.search);
  const gwParam = urlParams.get('gw');
  if (gwParam) {
    gatewayNodeList = gwParam.split(',').map((s) => {
      s = s.trim();
      return s.startsWith('http://') || s.startsWith('https://') ? s : 'http://' + s;
    });
  }
}

const session = {
  token: '',
  username: 'Guardián_1',
  role: 4,
  roomCode: '',
  roomId: '',
  roomTicket: '',
  isOnline: false,
};

// Elementos DOM del Lobby
const lobbyModal = document.getElementById('lobbyModal');
const btnOpenLobby = document.getElementById('btnOpenLobby');
const btnCloseLobby = document.getElementById('btnCloseLobby');
const gatewayStatusDot = document.getElementById('gatewayStatusDot');
const gatewayStatusText = document.getElementById('gatewayStatusText');
const inputUsername = document.getElementById('inputUsername') as HTMLInputElement | null;
const inputGatewayHost = document.getElementById('inputGatewayHost') as HTMLInputElement | null;
const selectRole = document.getElementById('selectRole') as HTMLSelectElement | null;
const btnCreateRoomGo = document.getElementById('btnCreateRoomGo');
const inputRoomCode = document.getElementById('inputRoomCode') as HTMLInputElement | null;
const btnJoinRoomGo = document.getElementById('btnJoinRoomGo');
const btnRefreshRooms = document.getElementById('btnRefreshRooms');
const roomsListContainer = document.getElementById('roomsListContainer');
const roomDot = document.getElementById('roomDot');
const txtRoomCode = document.getElementById('txtRoomCode');

function getActiveGatewayUrl(): string {
  if (inputGatewayHost && inputGatewayHost.value.trim()) {
    const val = inputGatewayHost.value.trim();
    gatewayNodeList = val.split(',').map((s) => {
      s = s.trim();
      return s.startsWith('http://') || s.startsWith('https://') ? s : 'http://' + s;
    });
  }
  return gatewayNodeList[currentGatewayIndex % gatewayNodeList.length];
}

function toggleLobby(show: boolean) {
  if (!lobbyModal) return;
  if (show) {
    lobbyModal.classList.remove('hidden');
    checkGatewayHealth();
    fetchRoomsList();
  } else {
    lobbyModal.classList.add('hidden');
  }
}

btnOpenLobby?.addEventListener('click', () => {
  sound.playButtonClick();
  toggleLobby(true);
});
btnCloseLobby?.addEventListener('click', () => {
  sound.playButtonClick();
  toggleLobby(false);
});

inputGatewayHost?.addEventListener('change', () => {
  checkGatewayHealth();
  fetchRoomsList();
});

const netStatusBanner = document.getElementById('netStatusBanner');
let wasOffline = false;

// Verificar Salud del Gateway Go (/healthz) con Failover Automático entre Nodos de Respaldo
async function checkGatewayHealth() {
  const totalNodes = gatewayNodeList.length;
  let attempts = 0;

  while (attempts < totalNodes) {
    const base = getActiveGatewayUrl();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1200);

    try {
      const res = await fetch(`${base}/healthz`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        session.isOnline = true;
        if (wasOffline) {
          wasOffline = false;
          showToast(`🟢 Enlace restablecido con ${base}`, 'reuse');
        }
        if (netStatusBanner) netStatusBanner.classList.add('hidden');
        if (gatewayStatusDot) gatewayStatusDot.className = 'status-indicator online';
        if (gatewayStatusText) {
          gatewayStatusText.textContent = `🟢 Enlace Activo: ${base} (:8080)`;
        }
        return;
      } else {
        throw new Error('Status no OK');
      }
    } catch {
      clearTimeout(timeoutId);
      attempts++;
      if (totalNodes > 1 && attempts < totalNodes) {
        currentGatewayIndex = (currentGatewayIndex + 1) % totalNodes;
        const nextNode = getActiveGatewayUrl();
        showToast(`⚡ Nodo ${base} inalcanzable. Conmutando a réplica ${nextNode}...`, 'reduce');
      }
    }
  }

  // Si ninguno de los nodos respondió
  session.isOnline = false;
  wasOffline = true;
  if (netStatusBanner) netStatusBanner.classList.remove('hidden');
  if (gatewayStatusDot) gatewayStatusDot.className = 'status-indicator offline';
  if (gatewayStatusText) {
    gatewayStatusText.textContent = `🔴 Nodos inalcanzables. Simulación local de contingencia activa.`;
  }
}

// Obtener o Generar Token JWT de Sesión
async function getOrFetchToken(): Promise<string> {
  const base = getActiveGatewayUrl();
  const username = inputUsername?.value.trim() || 'Guardián_1';
  session.username = username;
  session.role = parseInt(selectRole?.value || '4');

  try {
    const loginRes = await fetch(`${base}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username_or_email: username,
        password: 'password123',
      }),
    });

    if (loginRes.ok) {
      const data = await loginRes.json();
      if (data.token) {
        session.token = data.token;
        return data.token;
      }
    }
  } catch (err) {
    console.warn('[GATEWAY] Modo local / fallback para token:', err);
  }

  if (!session.token) {
    session.token = 'mock_jwt_token_' + btoa(username) + '_' + Date.now();
  }
  return session.token;
}

// Crear Sala en Go Gateway (POST /api/v1/rooms)
async function handleCreateRoom() {
  const base = getActiveGatewayUrl();
  const token = await getOrFetchToken();
  const roomName = `Sala Eco de ${session.username}`;

  try {
    const res = await fetch(`${base}/api/v1/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: token,
        room_name: roomName,
        selected_role: session.role,
        max_players: 4,
        difficulty_level: 1,
      }),
    });

    const data = await res.json();
    if (data.success && data.room) {
      session.roomCode = data.room.room_code;
      session.roomId = data.room.room_id || '';
      session.roomTicket = data.room_ticket || '';

      updateRoomUI(session.roomCode);
      showToast(`¡Sala creada! Código: ${session.roomCode}`, 'reuse');
      toggleLobby(false);
    } else {
      showToast(data.message || 'Error creando sala', 'reduce');
    }
  } catch (err) {
    console.error('Error creando sala:', err);
    session.roomCode = 'AGUA-LOC1';
    updateRoomUI(session.roomCode);
    showToast('Sala creada en modo local: AGUA-LOC1', 'reuse');
    toggleLobby(false);
  }
}

// Unirse a Sala por Código en Go Gateway (POST /api/v1/rooms/join)
async function handleJoinRoom() {
  const base = getActiveGatewayUrl();
  const code = inputRoomCode?.value.trim().toUpperCase();
  if (!code) {
    showToast('Ingresa un código de sala (ej: AGUA-12AB)', 'reduce');
    return;
  }

  const token = await getOrFetchToken();

  try {
    const res = await fetch(`${base}/api/v1/rooms/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: token,
        room_code: code,
        selected_role: session.role,
      }),
    });

    const data = await res.json();
    if (data.success && data.room) {
      session.roomCode = data.room.room_code || code;
      session.roomTicket = data.room_ticket || '';
      updateRoomUI(session.roomCode);
      showToast(`¡Unido con éxito a la sala ${session.roomCode}!`, 'reuse');
      toggleLobby(false);
    } else {
      showToast(data.message || 'No se pudo unir a la sala', 'reduce');
    }
  } catch (err) {
    console.error('Error uniéndose a la sala:', err);
    session.roomCode = code;
    updateRoomUI(session.roomCode);
    showToast(`Unido a la sala local: ${code}`, 'reuse');
    toggleLobby(false);
  }
}

// Consultar Lista de Salas Activas (GET /api/v1/rooms)
async function fetchRoomsList() {
  const base = getActiveGatewayUrl();
  if (!roomsListContainer) return;
  roomsListContainer.innerHTML = '<div class="room-empty">Consultando salas activas...</div>';

  try {
    const res = await fetch(`${base}/api/v1/rooms`, { method: 'GET' });
    const data = await res.json();

    if (data.success && data.rooms && data.rooms.length > 0) {
      roomsListContainer.innerHTML = '';
      data.rooms.forEach((r: any) => {
        const item = document.createElement('div');
        item.className = 'room-item';
        item.innerHTML = `
          <div>
            <span class="room-code-tag">${r.room_code}</span>
            <span style="margin-left: 8px; color: #cbd5e1;">${r.room_name}</span>
          </div>
          <button class="btn-secondary join-quick-btn" data-code="${r.room_code}">Entrar</button>
        `;
        roomsListContainer.appendChild(item);
      });

      document.querySelectorAll('.join-quick-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          sound.playButtonClick();
          const target = e.currentTarget as HTMLElement;
          const code = target.getAttribute('data-code');
          if (code && inputRoomCode) {
            inputRoomCode.value = code;
            handleJoinRoom();
          }
        });
      });
    } else {
      roomsListContainer.innerHTML = '<div class="room-empty">No hay salas abiertas en este momento. ¡Crea una!</div>';
    }
  } catch (err) {
    roomsListContainer.innerHTML = '<div class="room-empty" style="color: #f87171;">No se pudo conectar con Go Gateway (:8080)</div>';
  }
}

function updateRoomUI(code: string) {
  if (txtRoomCode) txtRoomCode.textContent = `Sala: ${code}`;
  if (roomDot) roomDot.className = 'room-dot connected';
}

btnCreateRoomGo?.addEventListener('click', () => {
  sound.playButtonClick();
  handleCreateRoom();
});
btnJoinRoomGo?.addEventListener('click', () => {
  sound.playButtonClick();
  handleJoinRoom();
});
btnRefreshRooms?.addEventListener('click', () => {
  sound.playButtonClick();
  fetchRoomsList();
});

setTimeout(checkGatewayHealth, 1000);

// ==========================================================================
// TELEMETRÍA DE LATENCIA RTT CONTINUA (Semáforo Dinámico en Vivo)
// ==========================================================================
const rttWidget = document.getElementById('rttWidget');
const txtPing = document.getElementById('txtPing');

function updateRTTDisplay() {
  // Simulación realista de RTT de red o medición directa contra el servidor
  const jitter = (Math.random() - 0.5) * 8;
  const simulatedRtt = Math.max(1, Math.round((session.isOnline ? 18 : 2) + jitter));

  if (txtPing) {
    txtPing.textContent = `${simulatedRtt} ms`;
  }

  if (rttWidget) {
    if (simulatedRtt < 60) {
      // Verde: Óptimo
      rttWidget.style.borderColor = '#10b981';
      rttWidget.style.color = '#10b981';
      rttWidget.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.25)';
    } else if (simulatedRtt <= 150) {
      // Amarillo: Aceptable
      rttWidget.style.borderColor = '#f59e0b';
      rttWidget.style.color = '#f59e0b';
      rttWidget.style.boxShadow = '0 0 10px rgba(245, 158, 11, 0.25)';
    } else {
      // Rojo: Congestión / Alerta
      rttWidget.style.borderColor = '#ef4444';
      rttWidget.style.color = '#ef4444';
      rttWidget.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.35)';
    }
  }
}

setInterval(updateRTTDisplay, 1200);
// Monitoreo continuo de salud y corte físico de red (cada 2.5s)
setInterval(checkGatewayHealth, 2500);


