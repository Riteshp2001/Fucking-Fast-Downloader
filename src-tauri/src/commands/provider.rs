use crate::providers::{GameDetail, ProviderRegistry, SearchResult};
use crate::providers::cloudflare::CloudflareHandler;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{AppHandle, State};
use tokio::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct ProviderStatus {
    pub name: String,
    pub enabled: bool,
    pub error: Option<String>,
}

#[tauri::command]
pub async fn list_providers(
    registry: State<'_, Arc<Mutex<ProviderRegistry>>>,
) -> Result<Vec<ProviderStatus>, String> {
    let registry = registry.lock().await;
    let statuses: Vec<ProviderStatus> = registry
        .list()
        .into_iter()
        .map(|s| ProviderStatus {
            name: s.name,
            enabled: s.enabled,
            error: s.error,
        })
        .collect();
    Ok(statuses)
}

#[tauri::command]
pub async fn search_provider(
    provider: String,
    query: String,
    registry: State<'_, Arc<Mutex<ProviderRegistry>>>,
) -> Result<Vec<SearchResult>, String> {
    let registry = registry.lock().await;
    registry
        .search(&provider, &query)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn fetch_game_detail(
    provider: String,
    url: String,
    registry: State<'_, Arc<Mutex<ProviderRegistry>>>,
) -> Result<GameDetail, String> {
    let registry = registry.lock().await;
    registry
        .fetch_details(&provider, &url)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn solve_provider_captcha(
    _provider: String,
    url: String,
    cf_handler: State<'_, Arc<Mutex<CloudflareHandler>>>,
    app: AppHandle,
) -> Result<(), String> {
    let cf = cf_handler.lock().await;
    cf.solve_captcha(&app, &url)
        .await
        .map_err(|e| e.to_string())
}
