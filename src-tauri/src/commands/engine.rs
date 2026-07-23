use crate::aria2::client::Aria2State;
use crate::engine;
use crate::error::AppError;
use crate::services;
use tauri::AppHandle;

use super::config::get_system_config;

/// Starts the bundled engine process with current system configuration.
/// Runs on a background thread to avoid blocking the WebView main thread.
///
/// NOTE: This ONLY spawns the bundled engine sidecar. It does NOT wait for
/// readiness or sync options. The frontend must call `wait_for_engine`
/// afterwards, which handles: probe → credential update → option sync.
#[tauri::command]
pub async fn start_engine_command(app: AppHandle) -> Result<(), AppError> {
    log::info!("engine:start-command");
    let app2 = app.clone();
    tokio::task::spawn_blocking(move || {
        let config = get_system_config(app2.clone())?;
        engine::start_engine(&app2, &config).map_err(AppError::Engine)
    })
    .await
    .map_err(|e| AppError::Engine(e.to_string()))?
}

/// Gracefully stops the running bundled engine process.
/// Runs on a background thread to avoid blocking the WebView main thread.
#[tauri::command]
pub async fn stop_engine_command(app: AppHandle) -> Result<(), AppError> {
    log::info!("engine:stop-command");
    tokio::task::spawn_blocking(move || engine::stop_engine(&app, false).map_err(AppError::Engine))
        .await
        .map_err(|e| AppError::Engine(e.to_string()))?
}

/// Stops and restarts the bundled engine with current system configuration.
/// Runs on a background thread to avoid blocking the WebView main thread
/// during the kill → sleep → cleanup → spawn sequence.
///
/// Same as `start_engine_command` — does NOT call `on_engine_ready`.
/// The frontend must call `wait_for_engine` afterwards.
#[tauri::command]
pub async fn restart_engine_command(app: AppHandle) -> Result<(), AppError> {
    log::info!("engine:restart-command");
    let app2 = app.clone();
    tokio::task::spawn_blocking(move || {
        let config = get_system_config(app2.clone())?;
        engine::restart_engine(&app2, &config).map_err(AppError::Engine)
    })
    .await
    .map_err(|e| AppError::Engine(e.to_string()))?
}

/// Rust-side health check: probes the Aria2 Next RPC endpoint with retries.
///
/// On successful probe, runs `on_engine_ready()` which:
///   1. Updates Aria2Client credentials
///   2. Refreshes RuntimeConfig
///   3. Syncs global options to aria2 via changeGlobalOption
///   4. Applies speed limit overrides
///
/// This ordering is critical — `on_engine_ready` sends RPC to Aria2 Next,
/// so it MUST run AFTER the probe confirms the engine is accepting connections.
#[tauri::command]
pub async fn wait_for_engine(app: AppHandle) -> Result<bool, AppError> {
    use tauri::Manager;
    const MAX_RETRIES: u32 = 5;
    const BASE_DELAY_MS: u64 = 200;

    let (port, secret) = services::read_engine_credentials_from_app(&app)?;

    // Update Aria2Client credentials BEFORE probing so the probe
    // targets the correct port/secret.
    if let Some(aria2) = app.try_state::<Aria2State>() {
        aria2.0.update_credentials(port, secret).await;
    }

    let aria2 = app
        .try_state::<Aria2State>()
        .ok_or_else(|| AppError::Engine("Aria2State not managed".into()))?;

    for i in 0..MAX_RETRIES {
        match aria2.0.get_version().await {
            Ok(_) => {
                log::info!("wait_for_engine: connected on attempt {}", i + 1);

                // Aria2 Next is confirmed ready — NOW safe to sync options.
                if let Err(e) = services::on_engine_ready(&app).await {
                    log::warn!("wait_for_engine: on_engine_ready failed: {e}");
                    // Non-fatal: engine is usable even if option sync fails.
                    // User can manually trigger re-sync from preferences.
                }

                return Ok(true);
            }
            Err(e) => {
                let delay = std::cmp::min(BASE_DELAY_MS * 2u64.pow(i), 3000);
                log::debug!(
                    "wait_for_engine: attempt {}/{} failed ({}), retry in {}ms",
                    i + 1,
                    MAX_RETRIES,
                    e,
                    delay
                );
                tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
            }
        }
    }

    log::warn!("wait_for_engine: all {} attempts failed", MAX_RETRIES);
    Ok(false)
}
