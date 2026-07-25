pub mod cache;
pub mod cloudflare;
pub mod error;
pub mod fitgirl;

use async_trait::async_trait;
pub use error::ProviderError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

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

pub struct ProviderRegistry {
    providers: HashMap<String, Box<dyn Provider>>,
}

impl ProviderRegistry {
    pub fn new() -> Self {
        Self {
            providers: HashMap::new(),
        }
    }

    pub fn register(&mut self, provider: Box<dyn Provider>) {
        let name = provider.name().to_string();
        self.providers.insert(name, provider);
    }

    pub fn get(&self, name: &str) -> Option<&dyn Provider> {
        self.providers.get(name).map(|b| b.as_ref())
    }

    pub fn list(&self) -> Vec<ProviderStatus> {
        self.providers
            .values()
            .map(|p| ProviderStatus {
                name: p.name().to_string(),
                enabled: p.enabled(),
                error: None,
            })
            .collect()
    }

    pub async fn search(&self, provider: &str, query: &str) -> Result<Vec<SearchResult>, ProviderError> {
        match self.get(provider) {
            Some(p) if p.enabled() => p.search(query).await,
            Some(_) => Err(ProviderError::Disabled),
            None => Err(ProviderError::NotFound(format!("Provider '{provider}' not found"))),
        }
    }

    pub async fn fetch_details(&self, provider: &str, url: &str) -> Result<GameDetail, ProviderError> {
        match self.get(provider) {
            Some(p) if p.enabled() => p.fetch_details(url).await,
            Some(_) => Err(ProviderError::Disabled),
            None => Err(ProviderError::NotFound(format!("Provider '{provider}' not found"))),
        }
    }
}
