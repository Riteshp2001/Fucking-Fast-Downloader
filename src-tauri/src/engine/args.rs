/// Builds the CLI argument list for spawning the bundled engine sidecar.
///
/// The whitelist of valid Aria2 Next options is loaded from the shared
/// `aria2Options.json` — the single source of truth also consumed by the
/// frontend (`src/shared/configKeys.ts`). Options managed exclusively by
/// `aria2.conf` are excluded from the whitelist to prevent store overrides.
use std::collections::HashSet;
use std::sync::OnceLock;

/// Shared engine-option metadata, embedded at compile time.
const ARIA2_OPTIONS_JSON: &str = include_str!("../../../src/shared/aria2Options.json");

#[derive(serde::Deserialize)]
struct Aria2Options {
    #[serde(rename = "engineOptions")]
    engine_options: Vec<String>,
    #[serde(rename = "nonHotReloadable")]
    non_hot_reloadable: Vec<String>,
}

fn aria2_options() -> &'static Aria2Options {
    static OPTIONS: OnceLock<Aria2Options> = OnceLock::new();
    OPTIONS.get_or_init(|| {
        serde_json::from_str(ARIA2_OPTIONS_JSON).expect("aria2Options.json is valid JSON")
    })
}

/// Every aria2 engine option the app may pass on the CLI or via RPC.
pub(crate) fn supported_engine_keys() -> &'static HashSet<&'static str> {
    static KEYS: OnceLock<HashSet<&'static str>> = OnceLock::new();
    KEYS.get_or_init(|| {
        aria2_options()
            .engine_options
            .iter()
            .map(String::as_str)
            .collect()
    })
}

/// Options aria2 rejects via `changeGlobalOption` (bound at process start).
pub(crate) fn non_hot_reloadable_keys() -> &'static HashSet<&'static str> {
    static KEYS: OnceLock<HashSet<&'static str>> = OnceLock::new();
    KEYS.get_or_init(|| {
        aria2_options()
            .non_hot_reloadable
            .iter()
            .map(String::as_str)
            .collect()
    })
}

const PROXY_CLEAR_KEYS: &[&str] = &[
    "all-proxy",
    "all-proxy-user",
    "all-proxy-passwd",
    "http-proxy",
    "http-proxy-user",
    "http-proxy-passwd",
    "https-proxy",
    "https-proxy-user",
    "https-proxy-passwd",
    "ftp-proxy",
    "ftp-proxy-user",
    "ftp-proxy-passwd",
    "no-proxy",
];

fn preserves_empty_value(key: &str) -> bool {
    PROXY_CLEAR_KEYS.contains(&key) || key == "seed-time"
}

#[derive(Clone, Copy, Default)]
pub(crate) struct ManagedEnginePaths<'a> {
    pub ed2k_bootstrap: Option<(&'a str, &'a str)>,
    pub bt_peer_blocklist: Option<&'a str>,
}

#[cfg(test)]
pub(crate) fn build_start_args(
    config: &serde_json::Value,
    conf_path: Option<&str>,
    session_path: &str,
    session_exists: bool,
    log_file_path: &str,
    log_level: &str,
) -> Vec<String> {
    build_start_args_impl(
        config,
        conf_path,
        session_path,
        session_exists,
        log_file_path,
        log_level,
        ManagedEnginePaths::default(),
    )
}

pub(crate) fn build_start_args_with_managed_paths(
    config: &serde_json::Value,
    conf_path: Option<&str>,
    session_path: &str,
    session_exists: bool,
    log_file_path: &str,
    log_level: &str,
    managed_paths: ManagedEnginePaths<'_>,
) -> Vec<String> {
    build_start_args_impl(
        config,
        conf_path,
        session_path,
        session_exists,
        log_file_path,
        log_level,
        managed_paths,
    )
}

fn build_start_args_impl(
    config: &serde_json::Value,
    conf_path: Option<&str>,
    session_path: &str,
    session_exists: bool,
    log_file_path: &str,
    log_level: &str,
    managed_paths: ManagedEnginePaths<'_>,
) -> Vec<String> {
    let mut args: Vec<String> = Vec::new();

    // Load bundled config file if available
    if let Some(path) = conf_path {
        args.push(format!("--conf-path={}", path));
    }

    // Session persistence: save active/paused downloads, restore on restart
    args.push(format!("--save-session={}", session_path));
    if session_exists {
        args.push(format!("--input-file={}", session_path));
    }

    args.push(format!("--log={log_file_path}"));
    args.push(format!("--log-level={log_level}"));
    args.push(format!(
        "--log-max-size={}",
        crate::log_policy::MAX_LOG_FILE_SIZE
    ));
    args.push(format!(
        "--log-max-files={}",
        crate::log_policy::MAX_LOG_FILES
    ));
    args.push("--quiet=true".to_string());

    // Check keep-sharing flag (app-level logic, not an engine option).
    // Frontend sends String("true"/"false"), so handle both Bool and String
    let keep_sharing = config
        .get("keep-sharing")
        .map(|v| match v {
            serde_json::Value::Bool(b) => *b,
            serde_json::Value::String(s) => s == "true",
            _ => false,
        })
        .unwrap_or(false);

    let allow_remote_access = config
        .get("allow-remote-access")
        .map(|v| match v {
            serde_json::Value::Bool(b) => *b,
            serde_json::Value::String(s) => s == "true",
            _ => false,
        })
        .unwrap_or(false);

    if let Some(obj) = config.as_object() {
        for (key, value) in obj {
            // Only pass whitelisted Aria2 Next keys.
            if !supported_engine_keys().contains(key.as_str()) {
                continue;
            }

            if matches!(
                key.as_str(),
                "log" | "log-file" | "log-level" | "log-max-size" | "log-max-files"
            ) {
                continue;
            }

            if key == "allow-remote-access" {
                continue;
            }

            let val_str = match value {
                serde_json::Value::String(s) => s.clone(),
                serde_json::Value::Number(n) => n.to_string(),
                serde_json::Value::Bool(b) => b.to_string(),
                _ => continue,
            };

            // Handle keep-sharing: skip seed-time if keep_sharing is true,
            // except an empty value, which clears a stored condition.
            if keep_sharing && key == "seed-time" && !val_str.is_empty() {
                continue;
            }

            // Skip empty values except proxy clear values. Empty proxy args
            // intentionally override environment proxy variables at startup.
            if val_str.is_empty() && !preserves_empty_value(key) {
                continue;
            }

            // Defensive: skip SOCKS proxy values that aria2 cannot handle.
            // aria2's HttpProxyOptionHandler only accepts http/https/ftp schemes;
            // socks4/socks5 URIs cause errorCode=28 and crash the engine.
            if key == "all-proxy" && val_str.to_ascii_lowercase().starts_with("socks") {
                log::warn!(
                    "Skipping unsupported proxy protocol for --all-proxy: {}",
                    val_str
                );
                continue;
            }

            // Handle keep-sharing: override seed-ratio to 0
            if keep_sharing && key == "seed-ratio" {
                args.push("--seed-ratio=0".to_string());
                continue;
            }

            args.push(format!("--{}={}", key, val_str));
        }
    }

    args.push(format!("--rpc-listen-all={allow_remote_access}"));
    args.push("--rpc-allow-origin-all=true".to_string());

    if let Some((server_met_path, nodes_dat_path)) = managed_paths.ed2k_bootstrap {
        args.push(format!("--ed2k-server-list={server_met_path}"));
        args.push(format!("--ed2k-node-list={nodes_dat_path}"));
    }
    if let Some(path) = managed_paths.bt_peer_blocklist {
        args.push(format!("--bt-peer-blocklist={path}"));
    }

    // If no conf file, ensure RPC is enabled
    if conf_path.is_none() {
        args.push("--enable-rpc=true".to_string());
    }

    args
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn build_args_passes_whitelisted_keys() {
        let config =
            json!({ "dir": "/tmp", "split": 16, "async-dns": "false", "enable-dht6": "true" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--dir=/tmp"));
        assert!(args.iter().any(|a| a == "--split=16"));
        assert!(args.iter().any(|a| a == "--async-dns=false"));
        assert!(args.iter().any(|a| a == "--enable-dht6=true"));
    }

    #[test]
    fn build_args_injects_managed_resource_paths() {
        let args = build_start_args_with_managed_paths(
            &json!({
                "ed2k-server-list": "/user/server.met",
                "ed2k-node-list": "/user/nodes.dat"
            }),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
            ManagedEnginePaths {
                ed2k_bootstrap: Some(("/cache/server.met", "/cache/nodes.dat")),
                bt_peer_blocklist: Some("/cache/peer-blocklist.txt"),
            },
        );

        assert!(!args
            .iter()
            .any(|a| a == "--ed2k-server-list=/user/server.met"));
        assert!(!args.iter().any(|a| a == "--ed2k-node-list=/user/nodes.dat"));
        assert!(args
            .iter()
            .any(|a| a == "--ed2k-server-list=/cache/server.met"));
        assert!(args
            .iter()
            .any(|a| a == "--ed2k-node-list=/cache/nodes.dat"));
        assert!(args
            .iter()
            .any(|a| a == "--bt-peer-blocklist=/cache/peer-blocklist.txt"));
    }

    #[test]
    fn build_args_injects_managed_engine_logging_options() {
        let args = build_start_args(
            &json!({}),
            Some("/etc/aria2.conf"),
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "info",
        );

        assert!(args.iter().any(|a| a == "--log=/tmp/aria2-next.log"));
        assert!(args.iter().any(|a| a == "--log-level=info"));
        assert!(args.iter().any(|a| a == "--log-max-size=52428800"));
        assert!(args.iter().any(|a| a == "--log-max-files=1"));
        assert!(args.iter().any(|a| a == "--quiet=true"));
        assert!(!args.iter().any(|a| a.starts_with("--log-file=")));
        assert!(!args.iter().any(|a| a.starts_with("--console-level=")));
    }

    #[test]
    fn build_args_rejects_user_logging_overrides() {
        let args = build_start_args(
            &json!({
                "log-file": "/tmp/user.log",
                "log-level": "error",
                "log-max-size": "2M",
                "log-max-files": "4"
            }),
            None,
            "/tmp/s.session",
            false,
            "/tmp/managed.log",
            "debug",
        );

        assert!(args.iter().any(|a| a == "--log=/tmp/managed.log"));
        assert!(args.iter().any(|a| a == "--log-level=debug"));
        assert!(args.iter().any(|a| a == "--quiet=true"));
        assert!(!args.iter().any(|a| a == "--log-file=/tmp/user.log"));
        assert!(!args.iter().any(|a| a == "--log=/tmp/user.log"));
        assert!(!args.iter().any(|a| a == "--log-level=error"));
        assert!(args.iter().any(|a| a == "--log-max-size=52428800"));
        assert!(args.iter().any(|a| a == "--log-max-files=1"));
        assert!(!args.iter().any(|a| a == "--log-max-size=2M"));
        assert!(!args.iter().any(|a| a == "--log-max-files=4"));
        assert!(!args.iter().any(|a| a.starts_with("--console-level=")));
    }

    #[test]
    fn build_args_does_not_emit_removed_torrent_metadata_option() {
        let args = build_start_args(
            &json!({
                "torrent-metadata": "start"
            }),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );

        assert!(!args.iter().any(|a| a.starts_with("--torrent-metadata=")));
    }

    #[test]
    fn build_args_keeps_magnet_metadata_cache_options_conf_managed() {
        let args = build_start_args(
            &json!({
                "bt-save-metadata": "false",
                "bt-load-saved-metadata": "false",
                "bt-seed-unverified": "false",
                "bt-hash-check-seed": "false",
                "bt-remove-unselected-file": "false"
            }),
            Some("/tmp/aria2.conf"),
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );

        assert!(!args.iter().any(|a| a.starts_with("--bt-save-metadata=")));
        assert!(!args
            .iter()
            .any(|a| a.starts_with("--bt-load-saved-metadata=")));
        assert!(!args.iter().any(|a| a.starts_with("--bt-seed-unverified=")));
        assert!(!args.iter().any(|a| a.starts_with("--bt-hash-check-seed=")));
        assert!(!args
            .iter()
            .any(|a| a.starts_with("--bt-remove-unselected-file=")));
    }

    #[test]
    fn build_args_does_not_emit_removed_proxy_mode_option() {
        let args = build_start_args(
            &json!({
                "proxy-mode": "manual",
                "all-proxy": "http://127.0.0.1:7890"
            }),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );

        assert!(!args.iter().any(|a| a.starts_with("--proxy-mode=")));
        assert!(args
            .iter()
            .any(|a| a == "--all-proxy=http://127.0.0.1:7890"));
    }

    #[test]
    fn build_args_rejects_non_whitelisted_keys() {
        let config = json!({ "dir": "/tmp", "not-a-real-key": "value", "keep-sharing": true });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("not-a-real-key")));
        assert!(!args.iter().any(|a| a.contains("keep-sharing")));
    }

    #[test]
    fn build_args_rejects_unsupported_engine_keys() {
        let config = json!({
            "not-supported": "false",
            "stale-local-key": "false",
            "future-unknown-key": "203.0.113.1"
        });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("not-supported")));
        assert!(!args.iter().any(|a| a.contains("stale-local-key")));
        assert!(!args.iter().any(|a| a.contains("future-unknown-key")));
    }

    #[test]
    fn build_args_keep_sharing_skips_seed_time() {
        let config = json!({ "keep-sharing": true, "seed-time": "60" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("seed-time")));
    }

    #[test]
    fn build_args_keep_sharing_preserves_empty_seed_time_clear() {
        let config = json!({ "keep-sharing": true, "seed-time": "" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--seed-time="));
    }

    #[test]
    fn build_args_keep_sharing_overrides_seed_ratio() {
        let config = json!({ "keep-sharing": true, "seed-ratio": "1.0" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--seed-ratio=0"));
    }

    #[test]
    fn build_args_passes_detach_share_only() {
        let config = json!({ "detach-share-only": "true" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--detach-share-only=true"));
    }

    #[test]
    fn build_args_skips_empty_values() {
        let config = json!({ "dir": "" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("--dir=")));
    }

    #[test]
    fn build_args_preserves_empty_proxy_values_to_override_environment() {
        let config = json!({
            "all-proxy": "",
            "all-proxy-user": "",
            "all-proxy-passwd": "",
            "http-proxy": "",
            "http-proxy-user": "",
            "http-proxy-passwd": "",
            "https-proxy": "",
            "https-proxy-user": "",
            "https-proxy-passwd": "",
            "ftp-proxy": "",
            "ftp-proxy-user": "",
            "ftp-proxy-passwd": "",
            "no-proxy": ""
        });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );

        assert!(args.iter().any(|a| a == "--all-proxy="));
        assert!(args.iter().any(|a| a == "--all-proxy-user="));
        assert!(args.iter().any(|a| a == "--all-proxy-passwd="));
        assert!(args.iter().any(|a| a == "--http-proxy="));
        assert!(args.iter().any(|a| a == "--https-proxy="));
        assert!(args.iter().any(|a| a == "--ftp-proxy="));
        assert!(args.iter().any(|a| a == "--no-proxy="));
    }

    #[test]
    fn build_args_loads_session_on_exists() {
        let args = build_start_args(
            &json!({}),
            None,
            "/tmp/s.session",
            true,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--input-file=/tmp/s.session"));
        assert!(args.iter().any(|a| a == "--save-session=/tmp/s.session"));
    }

    #[test]
    fn build_args_no_input_file_when_no_session() {
        let args = build_start_args(
            &json!({}),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("input-file")));
        assert!(args.iter().any(|a| a == "--save-session=/tmp/s.session"));
    }

    #[test]
    fn build_args_includes_conf_path() {
        let args = build_start_args(
            &json!({}),
            Some("/etc/aria2.conf"),
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--conf-path=/etc/aria2.conf"));
    }

    #[test]
    fn build_args_enables_rpc_without_conf() {
        let args = build_start_args(
            &json!({}),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--enable-rpc=true"));
        assert!(args.iter().any(|a| a == "--rpc-listen-all=false"));
        assert!(args.iter().any(|a| a == "--rpc-allow-origin-all=true"));
    }

    #[test]
    fn build_args_allows_remote_rpc_only_when_enabled() {
        let args = build_start_args(
            &json!({ "allow-remote-access": "true" }),
            None,
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--rpc-listen-all=true"));
        assert!(args.iter().any(|a| a == "--rpc-allow-origin-all=true"));
    }

    #[test]
    fn bundled_conf_uses_local_rpc_by_default() {
        const BUNDLED_CONF: &str = include_str!("../../binaries/aria2.conf");
        assert!(BUNDLED_CONF.contains("rpc-listen-all=false"));
        assert!(BUNDLED_CONF.contains("rpc-allow-origin-all=true"));
    }

    #[test]
    fn bundled_conf_does_not_seed_unverified_bt_files() {
        const BUNDLED_CONF: &str = include_str!("../../binaries/aria2.conf");
        assert!(BUNDLED_CONF.contains("bt-seed-unverified=false"));
        assert!(!BUNDLED_CONF.contains("bt-seed-unverified=true"));
    }

    #[test]
    fn build_args_no_rpc_enable_with_conf() {
        let args = build_start_args(
            &json!({}),
            Some("/etc/aria2.conf"),
            "/tmp/s.session",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("enable-rpc")));
    }

    #[test]
    fn build_args_keep_sharing_string_true() {
        // Frontend sends String("true"), not Bool(true)
        let config = json!({ "keep-sharing": "true", "seed-time": "30", "seed-ratio": "1.5" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.starts_with("--seed-time")));
        assert!(args.iter().any(|a| a == "--seed-ratio=0"));
    }

    #[test]
    fn build_args_keep_sharing_string_false_passes_seed_values() {
        let config = json!({ "keep-sharing": "false", "seed-time": "30", "seed-ratio": "1.5" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--seed-time=30"));
        assert!(args.iter().any(|a| a == "--seed-ratio=1.5"));
    }

    #[test]
    fn build_args_no_keep_sharing_passes_seed_values() {
        // When keep-sharing is absent entirely, seed values should pass through
        let config = json!({ "seed-time": "60", "seed-ratio": "2.0" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--seed-time=60"));
        assert!(args.iter().any(|a| a == "--seed-ratio=2.0"));
    }

    #[test]
    fn build_args_boolean_true_value_coerced() {
        let config = json!({ "continue": true });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--continue=true"));
    }

    #[test]
    fn build_args_boolean_false_value_coerced() {
        let config = json!({ "continue": false });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--continue=false"));
    }

    #[test]
    fn build_args_numeric_value_coerced() {
        let config = json!({ "max-concurrent-downloads": 5 });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(args.iter().any(|a| a == "--max-concurrent-downloads=5"));
    }

    #[test]
    fn build_args_excludes_conf_path_when_none() {
        let args = build_start_args(
            &json!({}),
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.starts_with("--conf-path")));
    }

    #[test]
    fn build_args_null_and_array_values_skipped() {
        let config = json!({ "dir": null, "header": ["X-Custom: val"] });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("--dir=")));
        // Arrays are not handled by the match — skipped via `_ => continue`
        assert!(!args.iter().any(|a| a.contains("--header=")));
    }

    #[test]
    fn build_args_force_save_rejected_from_cli() {
        // force-save is now per-download only (set via RPC addTorrent).
        // It must NOT be passed as a CLI arg — doing so makes it the global
        // default for ALL downloads, causing completed HTTP tasks to persist
        // in the session file and re-download on restart.
        // See: aria2 SessionSerializer.cc:288
        let config = json!({ "force-save": true });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("force-save")));
    }

    #[test]
    fn build_args_force_save_string_also_rejected() {
        let config = json!({ "force-save": "true" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(!args.iter().any(|a| a.contains("force-save")));
    }

    #[test]
    fn build_args_skips_socks5_proxy() {
        let config = json!({ "all-proxy": "socks5://127.0.0.1:1080", "dir": "/tmp" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(
            !args.iter().any(|a| a.contains("all-proxy")),
            "socks5 proxy should be filtered out"
        );
        assert!(args.iter().any(|a| a == "--dir=/tmp"));
    }

    #[test]
    fn build_args_skips_socks4_proxy() {
        let config = json!({ "all-proxy": "socks4://127.0.0.1:1080" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(
            !args.iter().any(|a| a.contains("all-proxy")),
            "socks4 proxy should be filtered out"
        );
    }

    #[test]
    fn build_args_skips_socks5h_proxy() {
        let config = json!({ "all-proxy": "SOCKS5://127.0.0.1:1080" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(
            !args.iter().any(|a| a.contains("all-proxy")),
            "SOCKS5 (uppercase) should be filtered out"
        );
    }

    #[test]
    fn build_args_passes_http_proxy() {
        let config = json!({ "all-proxy": "http://127.0.0.1:8080" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(
            args.iter()
                .any(|a| a == "--all-proxy=http://127.0.0.1:8080"),
            "HTTP proxy should pass through"
        );
    }

    #[test]
    fn build_args_passes_bare_host_port_proxy() {
        let config = json!({ "all-proxy": "127.0.0.1:8080" });
        let args = build_start_args(
            &config,
            None,
            "/tmp/s",
            false,
            "/tmp/aria2-next.log",
            "debug",
        );
        assert!(
            args.iter().any(|a| a == "--all-proxy=127.0.0.1:8080"),
            "Bare HOST:PORT proxy should pass through"
        );
    }
}
