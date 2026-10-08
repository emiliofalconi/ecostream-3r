use engine_rust::auth::ticket::TicketVerifier;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;

fn make_test_ticket(secret: &str, room_id: &str, user_id: &str, exp: i64) -> String {
    let payload_json = format!(
        r#"{{"room_id":"{}","user_id":"{}","username":"TestUser","role":1,"is_host":true,"exp":{}}}"#,
        room_id, user_id, exp
    );
    let b64 = URL_SAFE_NO_PAD.encode(payload_json.as_bytes());

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes()).unwrap();
    mac.update(b64.as_bytes());
    let sig_hex = hex::encode(mac.finalize().into_bytes());

    format!("{}.{}", b64, sig_hex)
}

#[test]
fn test_ticket_verification_valid() {
    let secret = "super_secret_eco_hmac_ticket_key_2026";
    let verifier = TicketVerifier::new(secret);

    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let ticket = make_test_ticket(secret, "rm_100", "usr_55", now + 60);

    let claims = verifier.verify(&ticket).expect("Ticket legítimo debe ser válido");
    assert_eq!(claims.room_id, "rm_100");
    assert_eq!(claims.user_id, "usr_55");
    assert_eq!(claims.username, "TestUser");
    assert_eq!(claims.role, 1);
    assert!(claims.is_host);
}

#[test]
fn test_ticket_tampered_payload_rejected() {
    let secret = "super_secret_eco_hmac_ticket_key_2026";
    let verifier = TicketVerifier::new(secret);

    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let ticket = make_test_ticket(secret, "rm_100", "usr_55", now + 60);

    // Alterar payload
    let parts: Vec<&str> = ticket.split('.').collect();
    let fake_b64 = URL_SAFE_NO_PAD.encode(r#"{"room_id":"rm_evil","user_id":"usr_55","exp":9999999999}"#);
    let tampered = format!("{}.{}", fake_b64, parts[1]);

    assert!(verifier.verify(&tampered).is_err());
}

#[test]
fn test_ticket_expired_rejected() {
    let secret = "super_secret_eco_hmac_ticket_key_2026";
    let verifier = TicketVerifier::new(secret);

    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let expired_ticket = make_test_ticket(secret, "rm_100", "usr_55", now - 10);

    assert!(verifier.verify(&expired_ticket).is_err());
}
