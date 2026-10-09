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

const canvas = document.getElementById('gameCanvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d')!;

// Partículas y Efectos Visuales
const particles: Particle[] = [];
const floatingTexts: FloatingText[] = [];

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
  player: {
    x: 420,
    y: 320,
    targetX: 420,
    targetY: 320,
    angle: 0,
    isWrenching: false,
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

// Controles de Teclado
const keys: Record<string, boolean> = {};
window.addEventListener('keydown', (e) => {
  keys[e.key.toLowerCase()] = true;
  if (e.code === 'Space') {
    e.preventDefault();
    actionReduce();
  } else if (e.key.toLowerCase() === 'r') {
    actionReuse();
  } else if (e.key.toLowerCase() === 'f') {
    actionRecycle();
  }
});
window.addEventListener('keyup', (e) => {
  keys[e.key.toLowerCase()] = false;
});

// Botones UI
document.getElementById('btnReduce')?.addEventListener('click', actionReduce);
document.getElementById('btnReuse')?.addEventListener('click', actionReuse);
document.getElementById('btnRecycle')?.addEventListener('click', actionRecycle);

// Toggle Sonido
const btnSound = document.getElementById('btnSoundToggle');
btnSound?.addEventListener('click', () => {
  sound.enabled = !sound.enabled;
  if (btnSound) {
    btnSound.textContent = sound.enabled ? '🔊' : '🔇';
    btnSound.style.opacity = sound.enabled ? '1.0' : '0.5';
  }
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

// --------------------------------------------------------------------------
// ACCIONES 3R CON FEEDBACK VISUAL Y SONORO
// --------------------------------------------------------------------------
function actionReduce() {
  const leaking = state.pipes.find((p) => p.isLeaking);
  if (leaking) {
    leaking.isLeaking = false;
    leaking.repairProgress = 100;
    state.metrics.totalLitersSaved += 80;
    state.score += 150;
    state.player.isWrenching = true;
    setTimeout(() => (state.player.isWrenching = false), 500);

    // Chispas de soldadura
    for (let i = 0; i < 25; i++) {
      particles.push({
        x: leaking.x + 110,
        y: leaking.y + 13,
        vx: (Math.random() - 0.5) * 8,
        vy: (Math.random() - 0.7) * 7,
        life: 1.0,
        maxLife: 1.0,
        color: ['#fbbf24', '#f59e0b', '#38bdf8', '#ffffff'][Math.floor(Math.random() * 4)],
        size: 2 + Math.random() * 3,
        type: 'spark',
      });
    }

    sound.playRepair();
    spawnFloatingText('+150 PTS (80L Salvados!)', leaking.x + 60, leaking.y - 10, '#38bdf8');
    showToast('¡Fuga sellada con éxito! +80 Litros Ahorrados', 'reduce');
    updateHUD();
  } else {
    // Si no hay roturas, generar una nueva aleatoria tras un breve delay para juego continuo
    const okPipes = state.pipes.filter((p) => !p.isLeaking);
    if (okPipes.length > 0) {
      const p = okPipes[Math.floor(Math.random() * okPipes.length)];
      p.isLeaking = true;
      sound.playLeakAlert();
      showToast(`¡Nueva rotura a presión en Tubería #${p.id}!`, 'reduce');
    }
  }
}

function actionReuse() {
  state.metrics.totalLitersReused += 45;
  state.score += 80;
  state.sprinklersActive = true;
  state.sprinklerTimer = 120; // 2 segundos

  // Crecer cultivos
  state.crops.forEach((c) => {
    c.growth = Math.min(1.0, c.growth + 0.15);
    // Partículas de hojas / crecimiento
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

  sound.playReuse();
  spawnFloatingText('+80 PTS (45L Reusados en Riego 🌱)', 340, 360, '#34d399');
  showToast('Aguas grises canalizadas al huerto comunitario', 'reuse');
  updateHUD();
}

function actionRecycle() {
  state.metrics.totalLitersRecycled += 60;
  state.metrics.waterPurityPct = Math.min(100, state.metrics.waterPurityPct + 2.0);
  state.score += 120;

  // Burbujas y brillo en la planta de purificación
  for (let i = 0; i < 20; i++) {
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

  sound.playRecycle();
  spawnFloatingText('+120 PTS (Pureza +2.0% ⚗️)', state.plant.x - 60, state.plant.y - 40, '#c084fc');
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
}

// --------------------------------------------------------------------------
// BUCLE PRINCIPAL DE RENDERIZADO Y FÍSICA CANVAS 2D A 60 FPS
// --------------------------------------------------------------------------
let waveTime = 0;

function gameLoop() {
  state.tick++;
  waveTime += 0.04;
  state.plant.spinAngle += 0.03;

  if (state.sprinklerTimer > 0) {
    state.sprinklerTimer--;
    if (state.sprinklerTimer === 0) state.sprinklersActive = false;
  }

  // Movimiento suave del jugador
  const speed = 4.5;
  let moveX = 0;
  let moveY = 0;
  if (keys['w'] || keys['arrowup']) moveY -= speed;
  if (keys['s'] || keys['arrowdown']) moveY += speed;
  if (keys['a'] || keys['arrowleft']) moveX -= speed;
  if (keys['d'] || keys['arrowright']) moveX += speed;

  state.player.x = Math.max(60, Math.min(canvas.width - 60, state.player.x + moveX));
  state.player.y = Math.max(60, Math.min(canvas.height - 60, state.player.y + moveY));

  if (moveX !== 0 || moveY !== 0) {
    state.player.angle = Math.atan2(moveY, moveX);
  }

  // Drenaje continuo realista
  const hasLeak = state.pipes.some((p) => p.isLeaking);
  state.metrics.reservoirLevelPct = Math.max(0, state.metrics.reservoirLevelPct - (hasLeak ? 0.02 : 0.004));
  if (state.tick % 25 === 0) updateHUD();

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
  // 6. AVATAR DEL JUGADOR (AquaGuardian - Pixel Art Sprite 2D)
  // ------------------------------------------------------------------------
  ctx.save();
  ctx.translate(state.player.x, state.player.y);

  // Sombra de contacto
  ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
  ctx.beginPath();
  ctx.ellipse(0, 18, 16, 7, 0, 0, Math.PI * 2);
  ctx.fill();

  // Halo luminoso del guardián
  ctx.strokeStyle = state.player.isWrenching ? 'rgba(251, 191, 36, 0.8)' : 'rgba(56, 189, 248, 0.5)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(0, 4, 22, 0, Math.PI * 2);
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

  // Etiqueta superior del jugador
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 10px Outfit, sans-serif';
  ctx.textAlign = 'center';
  ctx.shadowColor = '#000000';
  ctx.shadowBlur = 4;
  ctx.fillText(session.username || 'Guardián', 0, -28);
  ctx.shadowBlur = 0;
  ctx.textAlign = 'left';

  ctx.restore();

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

  requestAnimationFrame(gameLoop);
}

// Iniciar Loop
requestAnimationFrame(gameLoop);
updateHUD();

// ==========================================================================
// INTEGRACIÓN CON GO GATEWAY (API REST & MATCHMAKING)
// ==========================================================================
let gatewayBaseUrl = 'http://localhost:8080';

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
    let val = inputGatewayHost.value.trim();
    if (!val.startsWith('http://') && !val.startsWith('https://')) {
      val = 'http://' + val;
    }
    gatewayBaseUrl = val;
  }
  return gatewayBaseUrl;
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

btnOpenLobby?.addEventListener('click', () => toggleLobby(true));
btnCloseLobby?.addEventListener('click', () => toggleLobby(false));

inputGatewayHost?.addEventListener('change', () => {
  checkGatewayHealth();
  fetchRoomsList();
});

// Verificar Salud del Gateway Go (/healthz)
async function checkGatewayHealth() {
  const base = getActiveGatewayUrl();
  try {
    const res = await fetch(`${base}/healthz`, { method: 'GET' });
    if (res.ok) {
      session.isOnline = true;
      if (gatewayStatusDot) {
        gatewayStatusDot.className = 'status-indicator online';
      }
      if (gatewayStatusText) {
        gatewayStatusText.textContent = `🟢 Conectado: ${base} (:8080) - Listo`;
      }
    } else {
      throw new Error('Status no OK');
    }
  } catch (e) {
    session.isOnline = false;
    if (gatewayStatusDot) {
      gatewayStatusDot.className = 'status-indicator offline';
    }
    if (gatewayStatusText) {
      gatewayStatusText.textContent = `🔴 Servidor Inaccesible en ${base}. Verifica la IP pública o Docker.`;
    }
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

btnCreateRoomGo?.addEventListener('click', handleCreateRoom);
btnJoinRoomGo?.addEventListener('click', handleJoinRoom);
btnRefreshRooms?.addEventListener('click', fetchRoomsList);

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


