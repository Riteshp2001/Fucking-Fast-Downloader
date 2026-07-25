use crate::providers::error::ProviderError;
use rusqlite::{params, Connection};
use serde::{de::DeserializeOwned, Serialize};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct ProviderCache {
    db: Connection,
}

impl ProviderCache {
    pub fn open(db_path: &Path) -> Result<Self, ProviderError> {
        let db = Connection::open(db_path)
            .map_err(|e| ProviderError::Cache(format!("Failed to open cache DB: {e}")))?;

        db.execute_batch(
            "CREATE TABLE IF NOT EXISTS provider_cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );",
        )
        .map_err(|e| ProviderError::Cache(format!("Failed to create cache table: {e}")))?;

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;
        let _ = db.execute(
            "DELETE FROM provider_cache WHERE expires_at < ?1",
            params![now],
        );

        Ok(Self { db })
    }

    pub fn get<T: DeserializeOwned>(&self, key: &str) -> Option<T> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;
        let mut stmt = self
            .db
            .prepare("SELECT value FROM provider_cache WHERE key = ?1 AND expires_at > ?2")
            .ok()?;
        let value: String = stmt.query_row(params![key, now], |row| row.get(0)).ok()?;
        serde_json::from_str(&value).ok()
    }

    pub fn set<T: Serialize>(
        &self,
        key: &str,
        value: &T,
        ttl_secs: u64,
    ) -> Result<(), ProviderError> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;
        let expires_at = now + ttl_secs as i64;
        let json = serde_json::to_string(value)
            .map_err(|e| ProviderError::Cache(format!("Serialization error: {e}")))?;
        self.db
            .execute(
                "INSERT OR REPLACE INTO provider_cache (key, value, expires_at) VALUES (?1, ?2, ?3)",
                params![key, json, expires_at],
            )
            .map_err(|e| ProviderError::Cache(format!("Failed to insert cache: {e}")))?;
        Ok(())
    }
}
