use crate::error::AppError;
use crate::services::config::RuntimeConfigState;
use tauri::Manager;
use tauri_plugin_store::StoreExt;

/// Refreshes the Rust-side `RuntimeConfig` from the current `config.json` preferences.
///
/// Called by the frontend after any config save operation (`loadPreference`,
/// `savePreference`, `updateAndSave`, `resetToDefaults`).
#[tauri::command]
pub async fn refresh_runtime_config(app: tauri::AppHandle) -> Result<(), AppError> {
    let store = app
        .store("config.json")
        .map_err(|e| AppError::Store(format!("Failed to open config store: {e}")))?;

    let prefs = store
        .get("preferences")
        .ok_or_else(|| AppError::Store("No preferences key in config store".into()))?;

    let state = app.state::<RuntimeConfigState>();
    state
        .refresh_from_json(&prefs)
        .await
        .map_err(AppError::Store)?;

    Ok(())
}
