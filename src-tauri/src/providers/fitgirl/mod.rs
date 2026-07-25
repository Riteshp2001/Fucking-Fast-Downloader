pub mod fuckingfast;
pub mod parser;
pub mod types;

use async_trait::async_trait;
use reqwest::Client;
use std::sync::Arc;
use tauri::AppHandle;
use tokio::sync::Mutex;

use crate::providers::cache::ProviderCache;
use crate::providers::cloudflare::CloudflareHandler;
use crate::providers::error::ProviderError;
use crate::providers::{GameDetail, Provider, SearchResult};

const BASE_URL: &str = "https://fitgirl-repacks.site";
const CACHE_TTL_SEARCH: u64 = 3600;
const CACHE_TTL_DETAILS: u64 = 86400;
const MAX_RETRIES: u32 = 5;

pub struct FitGirlProvider {
    client: Client,
    cache: Arc<Mutex<ProviderCache>>,
    cloudflare: Arc<Mutex<CloudflareHandler>>,
    app_handle: AppHandle,
}

impl FitGirlProvider {
    pub fn new(
        cache: ProviderCache,
        cloudflare: Arc<Mutex<CloudflareHandler>>,
        app_handle: AppHandle,
    ) -> Self {
        let client = Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .expect("reqwest Client");

        Self {
            client,
            cache: Arc::new(Mutex::new(cache)),
            cloudflare,
            app_handle,
        }
    }

    async fn fetch_with_cloudflare(&self, url: &str) -> Result<String, ProviderError> {
        let mut last_error = ProviderError::Network("max retries exceeded".into());

        for attempt in 0..MAX_RETRIES {
            let cookie_header = {
                let cf = self.cloudflare.lock().await;
                cf.get_cookie_header().await
            };

            let mut req = self.client.get(url);
            if !cookie_header.is_empty() {
                req = req.header("Cookie", &cookie_header);
            }

            let resp = req.send().await?;

            if CloudflareHandler::is_guarded(&resp) {
                log::warn!(
                    "provider:fitgirl: ddos-guard detected on attempt {}/{}",
                    attempt + 1,
                    MAX_RETRIES
                );

                if let Some(set_cookie) = resp
                    .headers()
                    .get("set-cookie")
                    .and_then(|v| v.to_str().ok())
                {
                    let cf = self.cloudflare.lock().await;
                    cf.update_from_set_cookie(set_cookie, "fitgirl-repacks.site")
                        .await;
                }

                {
                    let cf = self.cloudflare.lock().await;
                    cf.solve_captcha(&self.app_handle, url).await?;
                }

                continue;
            }

            if resp.status().as_u16() == 429 {
                let retry_after = resp
                    .headers()
                    .get("retry-after")
                    .and_then(|v| v.to_str().ok())
                    .and_then(|s| s.parse::<u64>().ok())
                    .unwrap_or(5);

                log::warn!(
                    "provider:fitgirl: rate limited, retry after {}s",
                    retry_after
                );
                tokio::time::sleep(std::time::Duration::from_secs(retry_after)).await;
                continue;
            }

            if !resp.status().is_success() {
                last_error = ProviderError::Http(
                    resp.status().as_u16(),
                    resp.status()
                        .canonical_reason()
                        .unwrap_or("Unknown")
                        .to_string(),
                );
                continue;
            }

            return resp.text().await.map_err(ProviderError::from);
        }

        Err(last_error)
    }
}

#[async_trait]
impl Provider for FitGirlProvider {
    fn name(&self) -> &str {
        "fitgirl"
    }

    fn enabled(&self) -> bool {
        true
    }

    async fn search(&self, query: &str) -> Result<Vec<SearchResult>, ProviderError> {
        let cache_key = format!("fitgirl:search:{query}");
        {
            let cache = self.cache.lock().await;
            if let Some(results) = cache.get::<Vec<SearchResult>>(&cache_key) {
                log::debug!("provider:fitgirl: cache hit for search '{query}'");
                return Ok(results);
            }
        }

        if let Some(article_url) = fitgirl_article_url_from_query(query) {
            let html = self.fetch_with_cloudflare(&article_url).await?;
            let result = parser::parse_article_search_result(&html, &article_url)?;
            let results = vec![result];
            {
                let cache = self.cache.lock().await;
                let _ = cache.set(&cache_key, &results, CACHE_TTL_SEARCH);
            }
            return Ok(results);
        }

        let search_url = format!("{BASE_URL}/?s={}", urlencoding::encode(query));
        let html = self.fetch_with_cloudflare(&search_url).await?;
        let results = match parser::parse_search_results(&html) {
            Ok(results) => results,
            Err(search_error) => {
                if let Some(article_url) = fitgirl_slug_url_from_query(query) {
                    match self.fetch_with_cloudflare(&article_url).await {
                        Ok(article_html) => {
                            vec![parser::parse_article_search_result(
                                &article_html,
                                &article_url,
                            )?]
                        }
                        Err(_) => return Err(search_error),
                    }
                } else {
                    return Err(search_error);
                }
            }
        };

        {
            let cache = self.cache.lock().await;
            let _ = cache.set(&cache_key, &results, CACHE_TTL_SEARCH);
        }

        Ok(results)
    }

    async fn fetch_details(&self, url: &str) -> Result<GameDetail, ProviderError> {
        let cache_key = format!("fitgirl:detail:v2:{}", url);
        {
            let cache = self.cache.lock().await;
            if let Some(detail) = cache.get::<GameDetail>(&cache_key) {
                log::debug!("provider:fitgirl: cache hit for detail '{url}'");
                return Ok(detail);
            }
        }

        let html = self.fetch_with_cloudflare(url).await?;
        let page = parser::parse_game_article(&html)?;

        let detail = GameDetail {
            title: page.title,
            images: page.images,
            description: page.description,
            features: page.features,
            dlcs: page.dlcs,
            magnet_links: page.magnet_links,
            direct_links: Vec::new(),
            raw_fuckingfast_links: page.fuckingfast_links,
            repack_size: page.repack_size,
        };

        {
            let cache = self.cache.lock().await;
            let _ = cache.set(&cache_key, &detail, CACHE_TTL_DETAILS);
        }

        Ok(detail)
    }
}

fn fitgirl_article_url_from_query(query: &str) -> Option<String> {
    let parsed = url::Url::parse(query.trim()).ok()?;
    let host = parsed.host_str()?.to_ascii_lowercase();
    if host != "fitgirl-repacks.site" && !host.ends_with(".fitgirl-repacks.site") {
        return None;
    }

    let mut url = parsed;
    url.set_query(None);
    url.set_fragment(None);
    Some(url.to_string())
}

fn fitgirl_slug_url_from_query(query: &str) -> Option<String> {
    let trimmed = query.trim();
    if trimmed.contains("://") {
        return None;
    }

    let mut slug = String::new();
    let mut last_was_dash = false;
    for ch in trimmed.chars().flat_map(char::to_lowercase) {
        if ch.is_ascii_alphanumeric() {
            slug.push(ch);
            last_was_dash = false;
        } else if !last_was_dash && !slug.is_empty() {
            slug.push('-');
            last_was_dash = true;
        }
    }

    while slug.ends_with('-') {
        slug.pop();
    }

    if slug.is_empty() {
        None
    } else {
        Some(format!("{BASE_URL}/{slug}/"))
    }
}

#[cfg(test)]
mod tests {
    use super::{fitgirl_article_url_from_query, fitgirl_slug_url_from_query};

    #[test]
    fn accepts_direct_fitgirl_article_url() {
        assert_eq!(
            fitgirl_article_url_from_query("https://fitgirl-repacks.site/lifted/?x=1#comments"),
            Some("https://fitgirl-repacks.site/lifted/".to_string())
        );
    }

    #[test]
    fn builds_slug_url_from_plain_query() {
        assert_eq!(
            fitgirl_slug_url_from_query("Lifted"),
            Some("https://fitgirl-repacks.site/lifted/".to_string())
        );
    }
}
