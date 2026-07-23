use crate::engine;
use crate::error::AppError;
use serde_json::Value;
use tauri::AppHandle;
use tauri::Manager;
use tauri_plugin_store::StoreExt;

/// Reads all system-level configuration from the `system.json` store.
#[tauri::command]
pub fn get_system_config(app: AppHandle) -> Result<Value, AppError> {
    let store = app
        .store("system.json")
        .map_err(|e| AppError::Store(e.to_string()))?;
    let entries: serde_json::Map<String, Value> = store
        .entries()
        .into_iter()
        .map(|(k, v)| (k.to_string(), v.clone()))
        .collect();
    Ok(Value::Object(entries))
}

/// Merges the given key-value pairs into the `system.json` store.
#[tauri::command]
pub fn save_system_config(app: AppHandle, config: Value) -> Result<(), AppError> {
    let store = app
        .store("system.json")
        .map_err(|e| AppError::Store(e.to_string()))?;
    if let Some(obj) = config.as_object() {
        for (key, value) in obj {
            store.set(key.clone(), value.clone());
        }
    }
    log::debug!(
        "config:save-system keys={}",
        config.as_object().map_or(0, serde_json::Map::len)
    );
    Ok(())
}

#[tauri::command]
pub fn read_settings_backup_file(path: String) -> Result<String, AppError> {
    std::fs::read_to_string(&path)
        .map_err(|e| AppError::Io(format!("Failed to read settings backup: {e}")))
}

#[tauri::command]
pub fn write_settings_backup_file(path: String, content: String) -> Result<(), AppError> {
    std::fs::write(&path, content)
        .map_err(|e| AppError::Io(format!("Failed to write settings backup: {e}")))
}

/// Clears user, system, and preference stores, resetting the app to defaults.
/// Also removes the aria2 session file to prevent tasks from resurrecting.
#[tauri::command]
pub fn factory_reset(app: AppHandle) -> Result<(), AppError> {
    log::warn!("config:factory-reset");
    let user_store = app
        .store("user.json")
        .map_err(|e| AppError::Store(e.to_string()))?;
    user_store.clear();
    let system_store = app
        .store("system.json")
        .map_err(|e| AppError::Store(e.to_string()))?;
    system_store.clear();
    // Also clear config.json where frontend preferences are persisted
    let config_store = app
        .store("config.json")
        .map_err(|e| AppError::Store(e.to_string()))?;
    config_store.clear();

    // Remove aria2 session file so downloads don't reappear after restart
    clear_session_file_inner(&app)?;
    crate::commands::bt_blocklist::remove_bt_peer_blocklist_cache(&app)?;

    Ok(())
}

/// Removes the aria2 download session file.
/// Called by both factory reset and session reset flows.
#[tauri::command]
pub fn clear_session_file(app: AppHandle) -> Result<(), AppError> {
    clear_session_file_inner(&app)
}

fn clear_session_file_inner(app: &AppHandle) -> Result<(), AppError> {
    let session_path = app
        .path()
        .app_data_dir()
        .map_err(|e| AppError::Io(e.to_string()))?
        .join("download.session");
    if session_path.exists() {
        std::fs::remove_file(&session_path).map_err(|e| AppError::Io(e.to_string()))?;
        log::info!("engine:clear-session path={}", session_path.display());
    }
    Ok(())
}

/// Returns the absolute path to the bundled aria2.conf file.
///
/// Resolves via Tauri's resource directory so the path is correct in both
/// dev mode (`target/debug/`) and production bundles where resources live
/// in a platform-specific location (macOS `Contents/Resources/`, Linux
/// `/usr/lib/{app}/`, Windows beside the executable).
#[tauri::command]
pub fn get_engine_conf_path(app: AppHandle) -> Result<String, AppError> {
    let conf_path = app
        .path()
        .resolve("binaries/aria2.conf", tauri::path::BaseDirectory::Resource)
        .map_err(|e| AppError::Io(e.to_string()))?;
    Ok(engine::path_to_safe_string(&conf_path))
}
