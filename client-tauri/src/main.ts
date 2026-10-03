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

  if (elRes) elRes.textContent = `${state.metrics.reservoirLevelPct.toFixed(1)}%`;
  if (elBarRes) elBarRes.style.width = `${Math.max(0, state.metrics.reservoirLevelPct)}%`;

  if (elPur) elPur.textContent = `${state.metrics.waterPurityPct.toFixed(1)}%`;
  if (elBarPur) elBarPur.style.width = `${Math.max(0, state.metrics.waterPurityPct)}%`;

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
    // Tubería metálica
    ctx.fillStyle = pipe.isLeaking ? 'rgba(239, 68, 68, 0.25)' : 'rgba(51, 65, 85, 0.8)';
    ctx.strokeStyle = pipe.isLeaking ? '#ef4444' : '#64748b';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(pipe.x, pipe.y, pipe.w, pipe.h, 6);
    ctx.fill();
    ctx.stroke();

    // Texto de estado
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 11px Outfit, sans-serif';
    const statusText = pipe.isLeaking ? `Tubería #${pipe.id} [⚠️ ROTURA CRÍTICA]` : `Tubería #${pipe.id} [OK - Presión Estable]`;
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

  // Dibujar cultivos y aspersores
  state.crops.forEach((crop) => {
    // Parcela de tierra
    ctx.fillStyle = '#1e293b';
    ctx.beginPath();
    ctx.roundRect(crop.x - 5, crop.y - 5, 42, 36, 6);
    ctx.fill();

    // Planta según crecimiento
    const plantColor = crop.growth > 0.7 ? '#4ade80' : '#22c55e';
    ctx.fillStyle = plantColor;
    ctx.beginPath();
    const plantH = 10 + crop.growth * 16;
    ctx.arc(crop.x + 16, crop.y + 16, Math.max(4, plantH / 2.5), 0, Math.PI * 2);
    ctx.fill();

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
  // 6. AVATAR DEL JUGADOR (AquaGuardian)
  // ------------------------------------------------------------------------
  ctx.save();
  ctx.translate(state.player.x, state.player.y);

  // Sombra suave
  ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
  ctx.beginPath();
  ctx.ellipse(0, 16, 14, 6, 0, 0, Math.PI * 2);
  ctx.fill();

  // Aura del guardián
  ctx.fillStyle = '#0284c7';
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(0, 0, 18, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // Indicador de dirección / herramienta
  ctx.rotate(state.player.angle);
  ctx.fillStyle = state.player.isWrenching ? '#fbbf24' : '#ffffff';
  ctx.beginPath();
  ctx.arc(10, 0, 5, 0, Math.PI * 2);
  ctx.fill();

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
