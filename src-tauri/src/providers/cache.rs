// Cache layer — SQLite-backed provider cache
// Will store: key (provider:url_hash), value (JSON blob), ttl (timestamp)

use crate::providers::error::ProviderError;

pub struct ProviderCache {
    // placeholder — implemented in Task 3
}

impl ProviderCache {
    pub fn new() -> Self {
        Self {}
    }
}
