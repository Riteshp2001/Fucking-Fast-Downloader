use crate::error::AppError;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

/// A single tracker source URL that failed to fetch.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FailedTrackerSource {
    pub url: String,
    pub reason: String,
}

/// Structured result from fetching multiple tracker source URLs.
/// Captures both successful response bodies and per-URL failure details
/// so the frontend can show granular feedback to the user.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FetchTrackerSourcesResult {
    pub data: Vec<String>,
    pub failures: Vec<FailedTrackerSource>,
}

/// Event payload emitted per-tracker during [`probe_trackers`].
///
/// Each probe result is pushed to the frontend immediately via
/// `tracker-probe-result` so the UI can update rows progressively
/// instead of waiting for the entire batch to complete.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct TrackerProbeEvent {
    url: String,
    status: String,
}

/// Classifies a tracker URL's protocol to determine probing strategy.
///
/// - `"probeable"` — HTTP/HTTPS trackers that can be checked with HEAD requests
/// - `"not-probed"` — UDP/WS/WSS trackers that cannot be probed from HTTP
fn classify_tracker_protocol(url: &str) -> &'static str {
    let lower_url = url.to_ascii_lowercase();
    if lower_url.starts_with("udp://")
        || lower_url.starts_with("ws://")
        || lower_url.starts_with("wss://")
    {
        "not-probed"
    } else {
        "probeable"
    }
}

/// Probes a single tracker URL and returns its reachability status.
///
/// Pure function extracted from [`probe_trackers`] for testability.
/// Non-HTTP protocols (UDP, WS, WSS) are classified as `"not-probed"`
/// without network access; HTTP/HTTPS trackers receive a HEAD request.
async fn probe_single(client: &reqwest::Client, url: &str) -> &'static str {
    if classify_tracker_protocol(url) == "not-probed" {
        return "not-probed";
    }
    match client.head(url).send().await {
        Ok(_) => "online",
        Err(_) => "offline",
    }
}

/// Probes a list of tracker URLs for reachability, emitting results
/// progressively via the `tracker-probe-result` Tauri event.
///
/// Each URL is probed sequentially (HTTP HEAD with 5s timeout).
/// After each probe completes, a [`TrackerProbeEvent`] is emitted so
/// the frontend can update the corresponding table row immediately,
/// rather than waiting for all probes to finish.
///
/// UDP/WS/WSS trackers are marked `"not-probed"` without network access.
#[tauri::command]
pub async fn probe_trackers(app: AppHandle, urls: Vec<String>) -> Result<(), AppError> {
    log::debug!("tracker:probe urls={}", urls.len());

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .danger_accept_invalid_certs(true)
        .redirect(reqwest::redirect::Policy::limited(3))
        .build()
        .map_err(|e| AppError::Io(e.to_string()))?;

    for url in &urls {
        let status = probe_single(&client, url).await;
        let _ = app.emit(
            "tracker-probe-result",
            TrackerProbeEvent {
                url: url.clone(),
                status: status.to_string(),
            },
        );
    }

    Ok(())
}

/// Fetches tracker lists from external source URLs via the Rust HTTP client,
/// bypassing browser CORS restrictions that block webview-based requests.
///
/// Each URL is fetched sequentially (typical source count is 1–5).
/// Failed URLs are logged individually and captured in `failures`;
/// successful response bodies are returned in `data`.
#[tauri::command]
pub async fn fetch_tracker_sources(
    urls: Vec<String>,
    proxy_server: Option<String>,
) -> Result<FetchTrackerSourcesResult, AppError> {
    if urls.is_empty() {
        return Ok(FetchTrackerSourcesResult {
            data: vec![],
            failures: vec![],
        });
    }

    log::info!("TrackerSync: fetching from {} source(s)", urls.len());

    let builder = reqwest::Client::builder().timeout(std::time::Duration::from_secs(30));
    let client =
        crate::commands::http_client::apply_explicit_proxy(builder, &proxy_server, "TrackerSync")
            .build()
            .map_err(|e| AppError::Io(format!("failed to build HTTP client: {}", e)))?;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();

    let mut data = Vec::new();
    let mut failures = Vec::new();

    for url in &urls {
        let request_url = format!("{}?t={}", url, now);
        match client.get(&request_url).send().await {
            Ok(resp) => {
                let status = resp.status();
                if !status.is_success() {
                    let reason = format!("HTTP {}", status.as_u16());
                    log::warn!("TrackerSync: {} returned {}", url, reason);
                    failures.push(FailedTrackerSource {
                        url: url.clone(),
                        reason,
                    });
                    continue;
                }
                match resp.text().await {
                    Ok(body) => data.push(body),
                    Err(e) => {
                        let reason = e.to_string();
                        log::warn!("TrackerSync: failed to read body from {}: {}", url, reason);
                        failures.push(FailedTrackerSource {
                            url: url.clone(),
                            reason,
                        });
                    }
                }
            }
            Err(e) => {
                let reason = e.to_string();
                log::warn!("TrackerSync: failed to fetch {}: {}", url, reason);
                failures.push(FailedTrackerSource {
                    url: url.clone(),
                    reason,
                });
            }
        }
    }

    log::info!(
        "TrackerSync: completed {}/{} succeeded",
        data.len(),
        urls.len()
    );

    Ok(FetchTrackerSourcesResult { data, failures })
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── probe_single ──────────────────────────────────────────────────

    #[test]
    fn test_probe_single_classifies_udp_as_not_probed() {
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let client = reqwest::Client::new();
        let status = rt.block_on(probe_single(&client, "udp://tracker.example.com:6969"));
        assert_eq!(status, "not-probed");
    }

    #[test]
    fn test_probe_single_classifies_wss_as_not_probed() {
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let client = reqwest::Client::new();
        let status = rt.block_on(probe_single(&client, "wss://tracker.example.com/announce"));
        assert_eq!(status, "not-probed");
    }

    #[test]
    fn test_probe_single_classifies_ws_as_not_probed() {
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let client = reqwest::Client::new();
        let status = rt.block_on(probe_single(&client, "ws://tracker.example.com/announce"));
        assert_eq!(status, "not-probed");
    }

    #[test]
    fn test_probe_single_unreachable_http_returns_offline() {
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(5))
            .build()
            .expect("build client");
        let status = rt.block_on(probe_single(&client, "http://192.0.2.1:1/announce"));
        assert_eq!(status, "offline");
    }

    // ── classify_tracker_protocol ────────────────────────────────────

    #[test]
    fn classify_http_as_probeable() {
        assert_eq!(
            classify_tracker_protocol("http://tracker.example.com:6969/announce"),
            "probeable"
        );
    }

    #[test]
    fn classify_https_as_probeable() {
        assert_eq!(
            classify_tracker_protocol("https://tracker.example.com/announce"),
            "probeable"
        );
    }

    #[test]
    fn classify_udp_as_not_probed() {
        assert_eq!(
            classify_tracker_protocol("udp://tracker.example.com:6969"),
            "not-probed"
        );
    }

    #[test]
    fn classify_uppercase_udp_as_not_probed() {
        assert_eq!(
            classify_tracker_protocol("UDP://tracker.example.com:6969"),
            "not-probed"
        );
    }

    #[test]
    fn classify_wss_as_not_probed() {
        assert_eq!(
            classify_tracker_protocol("wss://tracker.example.com/announce"),
            "not-probed"
        );
    }

    #[test]
    fn classify_ws_as_not_probed() {
        assert_eq!(
            classify_tracker_protocol("ws://tracker.example.com/announce"),
            "not-probed"
        );
    }

    #[test]
    fn classify_empty_url_as_probeable() {
        // Empty/malformed URLs are not udp/wss, so they fall through to
        // HTTP probing which will fail gracefully with "offline"
        assert_eq!(classify_tracker_protocol(""), "probeable");
    }

    #[test]
    fn classify_magnet_as_probeable() {
        // Non-tracker schemes fall through to HTTP probing attempt
        assert_eq!(
            classify_tracker_protocol("magnet:?xt=urn:btih:abc"),
            "probeable"
        );
    }

    // ── fetch_tracker_sources ───────────────────────────────────────

    #[test]
    fn test_fetch_empty_urls_returns_empty_result() {
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let result = rt
            .block_on(fetch_tracker_sources(vec![], None))
            .expect("should succeed");
        assert!(result.data.is_empty());
        assert!(result.failures.is_empty());
    }

    #[test]
    fn test_fetch_unreachable_url_returns_failure() {
        let urls = vec!["http://192.0.2.1:1/trackers.txt".to_string()];
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let result = rt
            .block_on(fetch_tracker_sources(urls, None))
            .expect("should succeed — individual failures are captured, not errors");
        assert!(result.data.is_empty(), "no data from unreachable URL");
        assert_eq!(result.failures.len(), 1);
        assert_eq!(result.failures[0].url, "http://192.0.2.1:1/trackers.txt");
        assert!(
            !result.failures[0].reason.is_empty(),
            "failure reason must not be empty"
        );
    }

    #[test]
    fn test_fetch_result_serializes_to_camel_case() {
        let result = FetchTrackerSourcesResult {
            data: vec!["body1".to_string()],
            failures: vec![FailedTrackerSource {
                url: "http://example.com".to_string(),
                reason: "timeout".to_string(),
            }],
        };
        let json = serde_json::to_value(&result).expect("should serialize");
        assert_eq!(json["data"][0], "body1");
        assert_eq!(json["failures"][0]["url"], "http://example.com");
        assert_eq!(json["failures"][0]["reason"], "timeout");
    }

    #[test]
    fn test_fetch_result_empty_serializes_correctly() {
        let result = FetchTrackerSourcesResult {
            data: vec![],
            failures: vec![],
        };
        let json = serde_json::to_value(&result).expect("should serialize");
        assert!(json["data"]
            .as_array()
            .expect("data should be array")
            .is_empty());
        assert!(json["failures"]
            .as_array()
            .expect("failures should be array")
            .is_empty());
    }

    #[test]
    fn test_fetch_with_empty_proxy_ignores_proxy() {
        // Should not error when proxy_server is Some("") — treated as no proxy
        let rt = tokio::runtime::Runtime::new().expect("create tokio runtime");
        let result = rt
            .block_on(fetch_tracker_sources(
                vec!["http://192.0.2.1:1/trackers.txt".to_string()],
                Some("".to_string()),
            ))
            .expect("empty proxy should not cause error");
        // URL itself will fail, but the command itself should succeed
        assert_eq!(result.failures.len(), 1);
    }
}
