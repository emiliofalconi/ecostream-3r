// EcoStream 3R - Web Audio API Procedural Sound Synthesizer (Zero External Dependencies)
class SoundFX {
  private ctx: AudioContext | null = null;
  public enabled: boolean = true;
  private ambienceGain: GainNode | null = null;
  private ambienceOsc: OscillatorNode | null = null;

  private init() {
    if (!this.ctx && typeof window !== 'undefined') {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // 1. Sonido de Reparación / Soldadura de Tubería (1. Reducir)
  public playRepair() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    // Tono oscilante de soldadura metálica
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(260, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, this.ctx.currentTime + 0.16);

    gain.gain.setValueAtTime(0.18, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.22);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.22);

    // Chime metálico armónico secundario
    const ping = this.ctx.createOscillator();
    const pingGain = this.ctx.createGain();
    ping.type = 'sine';
    ping.frequency.setValueAtTime(1200, this.ctx.currentTime + 0.08);
    pingGain.gain.setValueAtTime(0.08, this.ctx.currentTime + 0.08);
    pingGain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.3);
    ping.connect(pingGain);
    pingGain.connect(this.ctx.destination);
    ping.start(this.ctx.currentTime + 0.08);
    ping.stop(this.ctx.currentTime + 0.3);
  }

  // 2. Sonido de Desvío / Riego de Huerto (2. Reusar)
  public playReuse() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(392, this.ctx.currentTime); // G4
    osc.frequency.exponentialRampToValueAtTime(659.25, this.ctx.currentTime + 0.18); // E5

    gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.25);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.25);
  }

  // 3. Sonido de Purificación / Planta de Filtro (3. Reciclar)
  public playRecycle() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    // Arpegio cristalino ascendente
    [523.25, 659.25, 783.99, 1046.5].forEach((freq, i) => {
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime + i * 0.07);

      gain.gain.setValueAtTime(0.14, this.ctx.currentTime + i * 0.07);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + i * 0.07 + 0.22);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(this.ctx.currentTime + i * 0.07);
      osc.stop(this.ctx.currentTime + i * 0.07 + 0.25);
    });
  }

  // 4. Sonido de Alerta de Fuga de Alta Presión
  public playLeakAlert() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'square';
    osc.frequency.setValueAtTime(330, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(140, this.ctx.currentTime + 0.28);

    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.3);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.3);
  }

  // 5. Sonido de Pasos del Avatar (Hierba / Suelo Húmedo)
  public playFootstep() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const baseFreq = 80 + Math.random() * 40;
    osc.type = 'sine';
    osc.frequency.setValueAtTime(baseFreq, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(30, this.ctx.currentTime + 0.06);

    gain.gain.setValueAtTime(0.05, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.07);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.07);
  }

  // 6. Sonido de Salpicadura de Agua / Gota (Splash)
  public playWaterSplash() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(900 + Math.random() * 300, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.09);

    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.1);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.1);
  }

  // 7. Click de Interfaz de Usuario / Botón
  public playButtonClick() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1200, this.ctx.currentTime + 0.04);

    gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.05);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.05);
  }

  // 8. Fanfarria de Victoria (Arpegio Triunfal 8-Bit)
  public playVictory() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const notes = [523.25, 659.25, 783.99, 1046.5, 1318.51]; // C5, E5, G5, C6, E6
    notes.forEach((freq, idx) => {
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.12);

      const dur = idx === notes.length - 1 ? 0.6 : 0.18;
      gain.gain.setValueAtTime(0.2, this.ctx.currentTime + idx * 0.12);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.12 + dur);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(this.ctx.currentTime + idx * 0.12);
      osc.stop(this.ctx.currentTime + idx * 0.12 + dur);
    });
  }

  // 9. Sonido de Derrota / Sequía Crítica
  public playDefeat() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const notes = [330.0, 311.13, 293.66, 261.63]; // E4, Eb4, D4, C4
    notes.forEach((freq, idx) => {
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.2);

      gain.gain.setValueAtTime(0.15, this.ctx.currentTime + idx * 0.2);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.2 + 0.28);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(this.ctx.currentTime + idx * 0.2);
      osc.stop(this.ctx.currentTime + idx * 0.2 + 0.3);
    });
  }

  // 10. Sonido de Impacto / Onda Expansiva (Sub-Bass Thud)
  public playShockwave() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(140, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(35, this.ctx.currentTime + 0.25);

    gain.gain.setValueAtTime(0.22, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.28);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.28);
  }

  // 11. Murmullo de Agua Ambiental Procedural (Breeze & River)
  public toggleAmbience(enable: boolean) {
    if (!enable) {
      if (this.ambienceGain && this.ctx) {
        this.ambienceGain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 0.5);
      }
      return;
    }

    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    if (this.ambienceOsc) return;

    // Oscilador de baja frecuencia modelando corriente de agua
    this.ambienceOsc = this.ctx.createOscillator();
    this.ambienceGain = this.ctx.createGain();
    this.ambienceOsc.type = 'sine';
    this.ambienceOsc.frequency.setValueAtTime(110, this.ctx.currentTime);

    this.ambienceGain.gain.setValueAtTime(0.0001, this.ctx.currentTime);
    this.ambienceGain.gain.exponentialRampToValueAtTime(0.02, this.ctx.currentTime + 2.0);

    this.ambienceOsc.connect(this.ambienceGain);
    this.ambienceGain.connect(this.ctx.destination);
    this.ambienceOsc.start();
  }
}

export const sound = new SoundFX();
