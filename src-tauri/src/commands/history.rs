//! Tauri commands exposing history database operations to the frontend.
//!
//! These commands serve as drop-in replacements for the frontend's direct
//! `tauri-plugin-sql` calls. The frontend store (`history.ts`) will be
//! updated to call these instead.

use crate::error::AppError;
use crate::history::{HistoryDbState, HistoryRecord};
use tauri::State;

/// Add or update a history record (upsert by GID).
#[tauri::command]
pub async fn history_add_record(
    state: State<'_, HistoryDbState>,
    record: HistoryRecord,
) -> Result<(), AppError> {
    state.0.add_record(&record).await
}

/// Query history records, optionally filtered by status and limited.
#[tauri::command]
pub async fn history_get_records(
    state: State<'_, HistoryDbState>,
    status: Option<String>,
    limit: Option<u32>,
) -> Result<Vec<HistoryRecord>, AppError> {
    state.0.get_records(status.as_deref(), limit).await
}

/// Remove a single record by GID.
#[tauri::command]
pub async fn history_remove_record(
    state: State<'_, HistoryDbState>,
    gid: String,
) -> Result<(), AppError> {
    state.0.remove_record(&gid).await
}

/// Clear records, optionally filtered by status.
#[tauri::command]
pub async fn history_clear_records(
    state: State<'_, HistoryDbState>,
    status: Option<String>,
) -> Result<(), AppError> {
    state.0.clear_records(status.as_deref()).await
}

/// Remove records whose GIDs are in the provided list.
#[tauri::command]
pub async fn history_remove_stale(
    state: State<'_, HistoryDbState>,
    gids: Vec<String>,
) -> Result<(), AppError> {
    state.0.remove_stale_records(&gids).await
}

/// Remove records matching a BT infoHash in the meta JSON column.
#[tauri::command]
pub async fn history_remove_by_info_hash(
    state: State<'_, HistoryDbState>,
    info_hash: String,
    exclude_gid: Option<String>,
) -> Result<(), AppError> {
    state
        .0
        .remove_by_info_hash(&info_hash, exclude_gid.as_deref())
        .await
}

/// Record a task birth timestamp.
#[tauri::command]
pub async fn history_record_birth(
    state: State<'_, HistoryDbState>,
    gid: String,
    added_at: String,
) -> Result<(), AppError> {
    state.0.record_task_birth(&gid, &added_at).await
}

/// Load all birth records.
#[tauri::command]
pub async fn history_load_births(
    state: State<'_, HistoryDbState>,
) -> Result<Vec<(String, String)>, AppError> {
    state.0.load_birth_records().await
}

/// Run PRAGMA integrity_check.
#[tauri::command]
pub async fn history_check_integrity(state: State<'_, HistoryDbState>) -> Result<String, AppError> {
    state.0.check_integrity().await
}
