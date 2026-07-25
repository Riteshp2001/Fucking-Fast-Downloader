use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
pub enum ProviderError {
    #[error("Network error: {0}")]
    Network(String),

    #[error("HTTP error: {0} {1}")]
    Http(u16, String),

    #[error("Parse error: {0}")]
    Parse(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Provider disabled")]
    Disabled,

    #[error("Timeout")]
    Timeout,

    #[error("Cache error: {0}")]
    Cache(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl From<reqwest::Error> for ProviderError {
    fn from(e: reqwest::Error) -> Self {
        if e.is_timeout() {
            ProviderError::Timeout
        } else if let Some(status) = e.status() {
            ProviderError::Http(
                status.as_u16(),
                status.canonical_reason().unwrap_or("Unknown").to_string(),
            )
        } else {
            ProviderError::Network(e.to_string())
        }
    }
}
