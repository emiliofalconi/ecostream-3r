// EcoStream 3R - AquaGuardians: Capa de Red y Telemetría en Vivo (Client-Tauri)
// Diseñado para operar transparentemente con Edge (localhost:8080) y Cloud (Render)
// sin modificar ningún estilo visual ni maquetación.

export interface NetworkState {
  gatewayUrl: string;
  isConnected: boolean;
  rttMs: number;
  username: string;
  token: string | null;
  roomId: string | null;
  roomCode: string | null;
  roomTicket: string | null;
  simulationEndpoint: string | null;
}

export class NetworkManager {
  public state: NetworkState = {
    gatewayUrl: 'https://ecostream-gateway.onrender.com',
    isConnected: false,
    rttMs: 0,
    username: 'AquaGuardian',
    token: null,
    roomId: null,
    roomCode: null,
    roomTicket: null,
    simulationEndpoint: null,
  };

  private pingTimer: number | null = null;
  private onTelemetryUpdate?: (state: NetworkState) => void;

  constructor() {
    // Extraer usuario opcional de la URL (?user=MiNombre) o de localStorage
    const params = new URLSearchParams(window.location.search);
    const paramUser = params.get('user');
    const savedUser = localStorage.getItem('ecostream_username');
    if (paramUser) {
      this.state.username = paramUser;
      localStorage.setItem('ecostream_username', paramUser);
    } else if (savedUser) {
      this.state.username = savedUser;
    }
  }

  /**
   * Auto-descubrimiento Edge-First: Intenta sonda local y si no responde usa Cloud Render.
   */
  public async discoverAndConnect(onUpdate?: (state: NetworkState) => void): Promise<void> {
    this.onTelemetryUpdate = onUpdate;

    const params = new URLSearchParams(window.location.search);
    const explicitGateway = params.get('gateway');

    if (explicitGateway) {
      this.state.gatewayUrl = explicitGateway;
    } else {
      try {
        // Sondeo rápido a Edge local con timeout de 800ms
        const localProbe = await fetch('http://localhost:8080/healthz', {
          method: 'GET',
          signal: AbortSignal.timeout(800),
        });
        if (localProbe.ok) {
          this.state.gatewayUrl = 'http://localhost:8080';
          console.log('[NETWORK] Edge Gateway Local detectado en http://localhost:8080');
        } else {
          this.state.gatewayUrl = 'https://ecostream-gateway.onrender.com';
        }
      } catch {
        this.state.gatewayUrl = 'https://ecostream-gateway.onrender.com';
        console.log('[NETWORK] Conectando a Cloud Render Gateway:', this.state.gatewayUrl);
      }
    }

    // Medición RTT inicial
    await this.ping();

    // Autenticación Passwordless y Obtención de Ticket HMAC
    await this.authenticateAndJoin();

    // Iniciar bucle de telemetría de latencia periódica (cada 3.5 segundos)
    this.startPingLoop();
  }

  /**
   * Mide la latencia RTT real de ida y vuelta contra el endpoint /healthz
   */
  public async ping(): Promise<number> {
    const t0 = performance.now();
    try {
      const resp = await fetch(`${this.state.gatewayUrl}/healthz?_t=${Date.now()}`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      if (resp.ok) {
        this.state.rttMs = Math.round(performance.now() - t0);
        this.state.isConnected = true;
      } else {
        this.state.isConnected = false;
      }
    } catch {
      this.state.isConnected = false;
      this.state.rttMs = 0;
    }

    if (this.onTelemetryUpdate) {
      this.onTelemetryUpdate(this.state);
    }
    return this.state.rttMs;
  }

  private startPingLoop(): void {
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.pingTimer = window.setInterval(() => {
      this.ping().catch(() => {});
    }, 3500);
  }

  /**
   * Autenticación automática por Nickname (sin contraseña) y obtención de RoomTicket
   */
  private async authenticateAndJoin(): Promise<void> {
    try {
      const loginResp = await fetch(`${this.state.gatewayUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: this.state.username }),
        signal: AbortSignal.timeout(5000),
      });

      if (!loginResp.ok) {
        console.warn('[NETWORK] Fallo en login Gateway HTTP', loginResp.status);
        return;
      }

      const loginData = await loginResp.json();
      this.state.token = loginData.token || loginData.access_token;
      console.log(`[NETWORK] Autenticado como ${this.state.username} (JWT obtenido)`);

      // Intentar unirse a sala AGUA42 o crear nueva
      const joinResp = await fetch(`${this.state.gatewayUrl}/api/v1/rooms/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.state.token}`,
        },
        body: JSON.stringify({ room_code: 'AGUA42', selected_role: 4 }),
        signal: AbortSignal.timeout(4000),
      });

      if (joinResp.ok) {
        const joinData = await joinResp.json();
        this.applyRoomData(joinData);
      } else {
        // Crear sala si no existe
        const createResp = await fetch(`${this.state.gatewayUrl}/api/v1/rooms/create`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.state.token}`,
          },
          body: JSON.stringify({
            room_name: 'Embalse Comunitario 3R',
            selected_role: 4,
            max_players: 4,
          }),
          signal: AbortSignal.timeout(4000),
        });
        if (createResp.ok) {
          const createData = await createResp.json();
          this.applyRoomData(createData);
        }
      }
    } catch (err) {
      console.warn('[NETWORK] Continuación en modo simulación autónomo (servidor offline o timeout):', err);
    }
  }

  private applyRoomData(data: any): void {
    const room = data.room || {};
    this.state.roomId = room.room_id || room.id || null;
    this.state.roomCode = room.room_code || 'AGUA42';
    this.state.roomTicket = data.room_ticket || null;
    this.state.simulationEndpoint = room.simulation_endpoint || null;
    console.log(`[NETWORK] Sala activa: [${this.state.roomCode}] | Ticket HMAC emitido.`);

    if (this.onTelemetryUpdate) {
      this.onTelemetryUpdate(this.state);
    }
  }

  /**
   * Notificación asíncrona de acción de las 3R realizada por el jugador
   */
  public async notifyAction(actionType: 'reduce' | 'reuse' | 'recycle', payload?: any): Promise<void> {
    if (!this.state.isConnected || !this.state.token || !this.state.roomId) return;
    try {
      // Disparo no bloqueante de telemetría de acción
      fetch(`${this.state.gatewayUrl}/api/v1/rooms/${this.state.roomId}/actions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.state.token}`,
        },
        body: JSON.stringify({ action: actionType, timestamp: Date.now(), ...payload }),
      }).catch(() => {});
    } catch {
      // Ignorar errores en acciones para no trabar el renderizado visual
    }
  }
}

export const networkManager = new NetworkManager();
