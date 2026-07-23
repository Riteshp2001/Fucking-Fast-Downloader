/// GeoIP peer country lookup using a bundled DB-IP Country Lite MMDB database.
///
/// Architecture follows the same pattern as qBittorrent's `GeoIPManager`:
/// load the database once at startup into managed state, then perform batch
/// lookups on demand.  The database is bundled as a Tauri resource (no
/// runtime download required).
///
/// Database: DB-IP Country Lite (CC BY 4.0)
///           <https://db-ip.com/db/download/ip-to-country-lite>
use std::collections::HashMap;
use std::net::IpAddr;
use std::sync::Arc;

use serde::Serialize;
use tauri::Manager;

use crate::error::AppError;

// ── Managed state ────────────────────────────────────────────────────

/// Holds the MMDB reader for the application lifetime.
///
/// Wrapped in `Arc<Option<…>>` so that startup never fails even if the
/// database file is missing — the reader is simply `None` and all
/// lookups return an empty map.
pub struct GeoIpState(pub Arc<Option<maxminddb::Reader<Vec<u8>>>>);

// ── Data types ───────────────────────────────────────────────────────

/// Geolocation result for a single IP address.
#[derive(Debug, Clone, Serialize)]
pub struct GeoInfo {
    pub country_code: String,
    pub country_name: String,
    pub continent: String,
}

// ── Initialisation ───────────────────────────────────────────────────

/// Resolves the bundled MMDB resource path and opens the reader.
///
/// Called once from `setup_app()`.  If the file is missing or corrupt,
/// the reader is `None` and a warning is logged — the application
/// continues normally, peer country flags are simply unavailable.
pub fn init_geoip(app: &tauri::AppHandle) -> GeoIpState {
    let reader = (|| -> Result<maxminddb::Reader<Vec<u8>>, String> {
        let resource_path = app
            .path()
            .resolve(
                "data/dbip-country-lite.mmdb",
                tauri::path::BaseDirectory::Resource,
            )
            .map_err(|e| format!("resolve path: {e}"))?;

        log::info!("geoip: loading database from {}", resource_path.display());

        let reader =
            maxminddb::Reader::open_readfile(&resource_path).map_err(|e| format!("open: {e}"))?;

        log::info!(
            "geoip: database loaded (type={}, build_epoch={})",
            reader.metadata.database_type,
            reader.metadata.build_epoch,
        );

        Ok(reader)
    })();

    match reader {
        Ok(r) => GeoIpState(Arc::new(Some(r))),
        Err(e) => {
            log::warn!("geoip: database unavailable — {e}");
            GeoIpState(Arc::new(None))
        }
    }
}

// ── Locale-aware name resolution ─────────────────────────────────────

/// Selects the best available localised name from the MMDB `Names` struct.
///
/// DB-IP Lite ships 8 languages: de, en, es, fr, ja, pt-BR, ru, zh-CN.
/// The frontend's i18n locale is mapped to the closest available field;
/// unsupported locales (18 of 26) fall back to English.
fn pick_name<'a>(names: &maxminddb::geoip2::Names<'a>, locale: &str) -> &'a str {
    let localised = match locale {
        "de" => names.german,
        "es" => names.spanish,
        "fr" => names.french,
        "ja" => names.japanese,
        "pt-BR" => names.brazilian_portuguese,
        "ru" => names.russian,
        "zh-CN" | "zh-TW" => names.simplified_chinese,
        _ => None, // 18 other locales → English fallback
    };
    localised.or(names.english).unwrap_or("")
}

// ── Tauri command ────────────────────────────────────────────────────

/// Batch-resolves peer IP addresses to country information.
///
/// Accepts a list of IP strings (IPv4 or IPv6) and the user's current
/// locale (e.g. `"zh-CN"`, `"ja"`, `"en-US"`).  Country and continent
/// names are returned in the closest available language, with English
/// as the fallback for unsupported locales.
///
/// Returns a map of successfully resolved IPs to their `GeoInfo`.
/// IPs that cannot be parsed or are not found in the database are
/// silently omitted — the frontend treats missing keys as "unknown".
///
/// Design: single IPC round-trip for all peers, avoiding N individual
/// calls that would thrash the IPC bridge on swarms with 100+ peers.
#[tauri::command]
pub fn lookup_peer_ips(
    ips: Vec<String>,
    locale: String,
    state: tauri::State<'_, GeoIpState>,
) -> Result<HashMap<String, GeoInfo>, AppError> {
    let reader: &maxminddb::Reader<Vec<u8>> = match state.0.as_ref() {
        Some(r) => r,
        None => return Ok(HashMap::new()),
    };

    let mut result = HashMap::with_capacity(ips.len());

    for ip_str in &ips {
        // Skip duplicates already resolved
        if result.contains_key(ip_str.as_str()) {
            continue;
        }

        let ip: IpAddr = match ip_str.parse() {
            Ok(ip) => ip,
            Err(_) => continue,
        };

        // lookup() returns LookupResult; decode() deserializes to geoip2::Country
        let lookup = match reader.lookup(ip) {
            Ok(r) => r,
            Err(_) => continue,
        };

        let record: maxminddb::geoip2::Country = match lookup.decode() {
            Ok(Some(r)) => r,
            _ => continue,
        };

        // geoip2::Country has non-Optional fields with Default values.
        // country::Country.iso_code is Option<&str>.
        // country::Country.names is a Names struct with .english: Option<&str>.
        let country_code = record.country.iso_code.unwrap_or("").to_string();
        let country_name = pick_name(&record.country.names, &locale).to_string();
        let continent = pick_name(&record.continent.names, &locale).to_string();

        if !country_code.is_empty() {
            result.insert(
                ip_str.clone(),
                GeoInfo {
                    country_code,
                    country_name,
                    continent,
                },
            );
        }
    }

    Ok(result)
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn geo_info_serialises_correctly() {
        let info = GeoInfo {
            country_code: "US".into(),
            country_name: "United States".into(),
            continent: "North America".into(),
        };
        let json = serde_json::to_value(&info).expect("serialise");
        assert_eq!(json["country_code"], "US");
        assert_eq!(json["country_name"], "United States");
        assert_eq!(json["continent"], "North America");
    }

    #[test]
    fn invalid_ip_is_silently_skipped() {
        let ip = "not-an-ip";
        assert!(ip.parse::<IpAddr>().is_err());
    }

    #[test]
    fn empty_state_returns_empty_map() {
        let state = GeoIpState(Arc::new(None));
        assert!(state.0.is_none());
    }
}
