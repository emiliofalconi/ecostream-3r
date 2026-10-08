use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoomTicketClaims {
    pub room_id: String,
    pub user_id: String,
    pub username: String,
    pub role: i32,
    pub is_host: bool,
    pub exp: i64,
}

#[derive(Debug)]
pub enum TicketError {
    InvalidFormat,
    InvalidSignature,
    Expired,
    DecodeError(String),
}

impl std::fmt::Display for TicketError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TicketError::InvalidFormat => write!(f, "Formato de ticket inválido"),
            TicketError::InvalidSignature => write!(f, "Firma HMAC del ticket inválida"),
            TicketError::Expired => write!(f, "El ticket ha expirado"),
            TicketError::DecodeError(msg) => write!(f, "Error al decodificar ticket: {}", msg),
        }
    }
}

impl std::error::Error for TicketError {}

pub struct TicketVerifier {
    secret: Vec<u8>,
}

impl TicketVerifier {
    pub fn new(secret: &str) -> Self {
        Self {
            secret: secret.as_bytes().to_vec(),
        }
    }

    pub fn verify(&self, ticket: &str) -> Result<RoomTicketClaims, TicketError> {
        let parts: Vec<&str> = ticket.split('.').collect();
        if parts.len() != 2 {
            return Err(TicketError::InvalidFormat);
        }

        let b64_payload = parts[0];
        let provided_sig_hex = parts[1];

        // Verificar firma HMAC-SHA256
        let mut mac = HmacSha256::new_from_slice(&self.secret)
            .map_err(|e| TicketError::DecodeError(e.to_string()))?;
        mac.update(b64_payload.as_bytes());

        let expected_sig = mac.finalize().into_bytes();
        let expected_sig_hex = hex::encode(expected_sig);

        // Comparación de firmas
        if provided_sig_hex.to_lowercase() != expected_sig_hex.to_lowercase() {
            return Err(TicketError::InvalidSignature);
        }

        // Decodificar Base64URL
        let payload_bytes = URL_SAFE_NO_PAD
            .decode(b64_payload)
            .map_err(|e| TicketError::DecodeError(e.to_string()))?;

        // Deserializar JSON
        let claims: RoomTicketClaims = serde_json::from_slice(&payload_bytes)
            .map_err(|e| TicketError::DecodeError(e.to_string()))?;

        // Verificar expiración
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;

        if now > claims.exp {
            return Err(TicketError::Expired);
        }

        Ok(claims)
    }
}
