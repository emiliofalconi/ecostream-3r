// EcoStream 3R - Cliente Web / Tauri (TypeScript + Canvas 2D)

interface WaterMetrics {
  reservoirLevelPct: number;
  waterPurityPct: number;
  totalLitersSaved: number;
  totalLitersReused: number;
  totalLitersRecycled: number;
}

interface GameState {
  tick: number;
  metrics: WaterMetrics;
  score: number;
  player: { x: number; y: number; vx: number; vy: number };
  pipes: Array<{ id: number; x: number; y: number; isLeaking: boolean }>;
  valves: Array<{ id: number; x: number; y: number; route: string }>;
  plant: { x: number; y: number; active: boolean };
}

const canvas = document.getElementById('gameCanvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d')!;

// Estado local reactivo
const state: GameState = {
  tick: 0,
  metrics: {
    reservoirLevelPct: 100.0,
    waterPurityPct: 96.0,
    totalLitersSaved: 0,
    totalLitersReused: 0,
    totalLitersRecycled: 0,
  },
  score: 0,
  player: { x: 350, y: 300, vx: 0, vy: 0 },
  pipes: [
    { id: 1, x: 300, y: 180, isLeaking: false },
    { id: 2, x: 480, y: 220, isLeaking: true },
    { id: 3, x: 360, y: 280, isLeaking: false },
  ],
  valves: [
    { id: 1, x: 320, y: 420, route: 'IRRIGATION' }
  ],
  plant: { x: 750, y: 350, active: true },
};

function resizeCanvas() {
  canvas.width = canvas.parentElement?.clientWidth || window.innerWidth;
  canvas.height = canvas.parentElement?.clientHeight || window.innerHeight - 70;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Controles de Teclado
const keys: Record<string, boolean> = {};
window.addEventListener('keydown', (e) => {
  keys[e.key.toLowerCase()] = true;
  if (e.code === 'Space') {
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

function actionReduce() {
  const leaking = state.pipes.find(p => p.isLeaking);
  if (leaking) {
    leaking.isLeaking = false;
    state.metrics.totalLitersSaved += 80;
    state.score += 150;
    updateHUD();
  }
}

function actionReuse() {
  state.metrics.totalLitersReused += 40;
  state.score += 60;
  updateHUD();
}

function actionRecycle() {
  state.metrics.totalLitersRecycled += 50;
  state.metrics.waterPurityPct = Math.min(100, state.metrics.waterPurityPct + 1.5);
  state.score += 100;
  updateHUD();
}

function updateHUD() {
  const elRes = document.getElementById('txtReservoir');
  const elPur = document.getElementById('txtPurity');
  const elScr = document.getElementById('txtScore');
  const elSav = document.getElementById('txtSaved');

  if (elRes) elRes.textContent = `${state.metrics.reservoirLevelPct.toFixed(1)}%`;
  if (elPur) elPur.textContent = `${state.metrics.waterPurityPct.toFixed(1)}%`;
  if (elScr) elScr.textContent = `${state.score} pts`;
  if (elSav) elSav.textContent = `${state.metrics.totalLitersSaved} L`;
}

// Bucle de Renderizado y Física Canvas 2D
let waveOffset = 0;
function gameLoop() {
  state.tick++;
  waveOffset += 0.05;

  // Movimiento del jugador
  const speed = 4.0;
  if (keys['w'] || keys['arrowup']) state.player.y = Math.max(50, state.player.y - speed);
  if (keys['s'] || keys['arrowdown']) state.player.y = Math.min(canvas.height - 50, state.player.y + speed);
  if (keys['a'] || keys['arrowleft']) state.player.x = Math.max(50, state.player.x - speed);
  if (keys['d'] || keys['arrowright']) state.player.x = Math.min(canvas.width - 50, state.player.x + speed);

  // Drenaje continuo del embalse
  const hasLeak = state.pipes.some(p => p.isLeaking);
  state.metrics.reservoirLevelPct = Math.max(0, state.metrics.reservoirLevelPct - (hasLeak ? 0.015 : 0.003));
  if (state.tick % 30 === 0) updateHUD();

  // 1. Limpiar fondo
  ctx.fillStyle = '#090d16';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 2. Dibujar Embalse Comunal (Zona Izquierda)
  const resW = 200;
  const resH = canvas.height - 80;
  const resX = 40;
  const resY = 40;

  ctx.fillStyle = '#0c4a6e';
  ctx.beginPath();
  ctx.roundRect(resX, resY, resW, resH, 12);
  ctx.fill();

  const fillH = resH * (state.metrics.reservoirLevelPct / 100.0);
  ctx.fillStyle = '#0284c7';
  ctx.beginPath();
  ctx.roundRect(resX, resY + (resH - fillH), resW, fillH, [0, 0, 12, 12]);
  ctx.fill();

  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 14px Outfit, sans-serif';
  ctx.fillText(`💧 EMBALSE: ${state.metrics.reservoirLevelPct.toFixed(1)}%`, resX + 20, resY + 30);

  // 3. Dibujar Zona 1: REDUCIR (Tuberías)
  state.pipes.forEach((pipe) => {
    ctx.fillStyle = pipe.isLeaking ? '#ef4444' : '#64748b';
    ctx.beginPath();
    ctx.roundRect(pipe.x, pipe.y, 160, 24, 6);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.font = '11px Outfit, sans-serif';
    ctx.fillText(`Tubería #${pipe.id} ${pipe.isLeaking ? '⚠️ ¡FUGA!' : '✅ OK'}`, pipe.x + 10, pipe.y + 16);

    // Partículas animadas de fuga de agua
    if (pipe.isLeaking) {
      ctx.fillStyle = 'rgba(56, 189, 248, 0.8)';
      for (let i = 0; i < 3; i++) {
        const px = pipe.x + 80 + Math.sin(waveOffset + i) * 15;
        const py = pipe.y - 10 - (i * 8);
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  });

  // 4. Dibujar Zona 2: REUSAR (Huerto Agrícola)
  ctx.fillStyle = 'rgba(20, 83, 45, 0.6)';
  ctx.strokeStyle = '#22c55e';
  ctx.beginPath();
  ctx.roundRect(280, 360, 240, 160, 10);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#86efac';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText('🌱 2. REUSAR: Huertos de Riego', 295, 385);
  ctx.fillStyle = '#dcfce7';
  ctx.font = '12px Outfit, sans-serif';
  ctx.fillText(`Aguas grises recirculadas: ${state.metrics.totalLitersReused} L`, 295, 415);

  // 5. Dibujar Zona 3: RECICLAR (Planta de Filtrado Biológico)
  ctx.fillStyle = 'rgba(88, 28, 135, 0.6)';
  ctx.strokeStyle = '#a855f7';
  ctx.beginPath();
  ctx.roundRect(state.plant.x - 120, state.plant.y - 100, 240, 220, 10);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#d8b4fe';
  ctx.font = 'bold 13px Outfit, sans-serif';
  ctx.fillText('⚗️ 3. RECICLAR: Planta Biológica', state.plant.x - 105, state.plant.y - 75);
  ctx.fillStyle = '#f3e8ff';
  ctx.font = '12px Outfit, sans-serif';
  ctx.fillText(`Pureza: ${state.metrics.waterPurityPct.toFixed(1)}%`, state.plant.x - 105, state.plant.y - 45);
  ctx.fillText(`Descontaminado: ${state.metrics.totalLitersRecycled} L`, state.plant.x - 105, state.plant.y - 20);

  // 6. Dibujar Avatar del Jugador
  ctx.fillStyle = '#0ea5e9';
  ctx.beginPath();
  ctx.arc(state.player.x, state.player.y, 16, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 10px Outfit, sans-serif';
  ctx.fillText('TÚ', state.player.x - 6, state.player.y + 4);

  requestAnimationFrame(gameLoop);
}

// Iniciar Loop
requestAnimationFrame(gameLoop);
