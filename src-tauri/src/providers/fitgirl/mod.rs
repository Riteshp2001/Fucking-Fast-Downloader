pub mod parser;
pub mod types;

use async_trait::async_trait;
use crate::providers::{GameDetail, Provider, ProviderError, SearchResult};

pub struct FitGirlProvider;

#[async_trait]
impl Provider for FitGirlProvider {
    fn name(&self) -> &str { "fitgirl" }
    fn enabled(&self) -> bool { true }

    async fn search(&self, _query: &str) -> Result<Vec<SearchResult>, ProviderError> {
        Err(ProviderError::Internal("not implemented".into()))
    }

    async fn fetch_details(&self, _url: &str) -> Result<GameDetail, ProviderError> {
        Err(ProviderError::Internal("not implemented".into()))
    }
}
