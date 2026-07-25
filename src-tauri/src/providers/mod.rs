pub mod cache;
pub mod cloudflare;
pub mod error;
pub mod fitgirl;

use async_trait::async_trait;
use error::ProviderError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub title: String,
    pub url: String,
    pub image: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub size: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameDetail {
    pub title: String,
    pub images: Vec<String>,
    pub description: String,
    pub features: Vec<String>,
    pub dlcs: Vec<String>,
    pub magnet_links: Vec<String>,
    pub repack_size: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectLink {
    pub url: String,
    pub filename: String,
    pub size: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderStatus {
    pub name: String,
    pub enabled: bool,
    pub error: Option<String>,
}

#[async_trait]
pub trait Provider: Send + Sync {
    fn name(&self) -> &str;
    fn enabled(&self) -> bool;
    async fn search(&self, query: &str) -> Result<Vec<SearchResult>, ProviderError>;
    async fn fetch_details(&self, url: &str) -> Result<GameDetail, ProviderError>;
}
