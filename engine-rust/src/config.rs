use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub simulation_port: u16,
    pub tick_rate_hz: u64,
    pub reconnect_grace_seconds: u64,
    pub hmac_secret: String,
    pub gateway_internal_url: String,
}

impl Config {
    pub fn from_env() -> Self {
        // En Render o entornos PaaS estándar, el puerto del contenedor se asigna en PORT
        let simulation_port = env::var("PORT")
            .or_else(|_| env::var("SIMULATION_GRPC_PORT"))
            .ok()
            .and_then(|p| p.parse().ok())
            .unwrap_or(50052);

        let tick_rate_hz = env::var("TICK_RATE_HZ")
            .ok()
            .and_then(|r| r.parse().ok())
            .unwrap_or(20);

        let reconnect_grace_seconds = env::var("RECONNECT_GRACE_SECONDS")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(10);

        let hmac_secret = env::var("HMAC_SECRET")
            .unwrap_or_else(|_| "super_secret_eco_hmac_ticket_key_2026".to_string());

        let gateway_internal_url = env::var("GATEWAY_INTERNAL_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:50051".to_string());

        Self {
            simulation_port,
            tick_rate_hz,
            reconnect_grace_seconds,
            hmac_secret,
            gateway_internal_url,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_port_and_defaults() {
        env::remove_var("PORT");
        env::remove_var("SIMULATION_GRPC_PORT");
        let cfg = Config::from_env();
        assert_eq!(cfg.simulation_port, 50052);
        assert_eq!(cfg.tick_rate_hz, 20);

        env::set_var("PORT", "50099");
        let cfg_override = Config::from_env();
        assert_eq!(cfg_override.simulation_port, 50099);
        env::remove_var("PORT");
    }
}
