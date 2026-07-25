use crate::providers::error::ProviderError;
use regex::Regex;
use reqwest::{header, Client};
use std::time::Duration;

const BASE_URL: &str = "https://fuckingfast.co";
const MAX_RETRIES: u32 = 3;

pub struct FuckingFastResolver {
    client: Client,
}

impl FuckingFastResolver {
    pub fn new() -> Self {
        let client = Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            .timeout(Duration::from_secs(20))
            .cookie_store(true)
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .expect("reqwest Client");

        Self { client }
    }

    pub async fn resolve(&self, link: &str) -> Result<String, ProviderError> {
        if is_direct_download_url(link) {
            return Ok(link.to_string());
        }

        let file_id = extract_file_id(link)
            .ok_or_else(|| ProviderError::Parse(format!("Invalid FuckingFast link: {link}")))?;
        let clean_url = format!("{BASE_URL}/{file_id}");
        let post_url = format!("{BASE_URL}/f/{file_id}/go");
        let mut last_error = ProviderError::Network("FuckingFast resolve failed".into());

        match self.fetch_page_direct_url(&clean_url).await {
            Ok(Some(url)) => return Ok(url),
            Ok(None) => {}
            Err(error) => last_error = error,
        }

        // Older FuckingFast pages return direct download links via htmx headers
        // on POST. Keep this as a fallback for pages that do not expose /dl/
        // links in their HTML/JavaScript.
        match self.post_go(&post_url, &clean_url).await {
            Ok(url) => return Ok(url),
            Err(error) => last_error = error,
        }

        for attempt in 0..MAX_RETRIES {
            if attempt > 0 {
                tokio::time::sleep(Duration::from_secs(2 * attempt as u64)).await;
            }

            match self.fetch_page_direct_url(&clean_url).await {
                Ok(Some(url)) => return Ok(url),
                Ok(None) => {}
                Err(error) => last_error = error,
            }

            match self.post_go(&post_url, &clean_url).await {
                Ok(url) => return Ok(url),
                Err(error) => last_error = error,
            }
        }

        Err(last_error)
    }

    async fn fetch_page_direct_url(&self, clean_url: &str) -> Result<Option<String>, ProviderError> {
        let resp = self
            .client
            .get(clean_url)
            .header(header::ACCEPT, "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8")
            .header(header::ACCEPT_LANGUAGE, "en-US,en;q=0.9")
            .header(header::CACHE_CONTROL, "no-cache")
            .header(header::PRAGMA, "no-cache")
            .header(header::REFERER, "https://fitgirl-repacks.site/")
            .header(header::UPGRADE_INSECURE_REQUESTS, "1")
            .header("Sec-Fetch-Dest", "document")
            .header("Sec-Fetch-Mode", "navigate")
            .header("Sec-Fetch-Site", "cross-site")
            .send()
            .await?;

        let status = resp.status();
        let reason = status.canonical_reason().unwrap_or("Unknown").to_string();
        let body = resp.text().await.map_err(ProviderError::from)?;

        if let Some(url) = extract_direct_download_url(&body) {
            return Ok(Some(url));
        }

        if is_rate_limited_body(&body) {
            return Err(ProviderError::Http(
                429,
                "FuckingFast rate limit detected; wait a few minutes and retry".into(),
            ));
        }

        if !status.is_success() {
            return Err(ProviderError::Http(status.as_u16(), reason));
        }

        Ok(None)
    }

    async fn post_go(&self, post_url: &str, clean_url: &str) -> Result<String, ProviderError> {
        let resp = self
            .client
            .post(post_url)
            .header(header::ACCEPT, "*/*")
            .header(header::ACCEPT_LANGUAGE, "en-US,en;q=0.9")
            .header(header::CACHE_CONTROL, "no-cache")
            .header(header::CONTENT_TYPE, "application/x-www-form-urlencoded")
            .header(header::ORIGIN, BASE_URL)
            .header(header::PRAGMA, "no-cache")
            .header(header::REFERER, clean_url)
            .header("HX-Current-URL", clean_url)
            .header("HX-Request", "true")
            .body("")
            .send()
            .await?;

        let status = resp.status();
        let header_redirect = resp
            .headers()
            .get("hx-redirect")
            .or_else(|| resp.headers().get("hx-location"))
            .or_else(|| resp.headers().get(header::LOCATION))
            .and_then(|value| value.to_str().ok())
            .and_then(|value| normalize_redirect_url(clean_url, value).ok());

        if let Some(url) = header_redirect {
            return Ok(url);
        }

        let body = resp.text().await.map_err(ProviderError::from)?;
        if let Some(url) = extract_direct_download_url(&body) {
            return Ok(url);
        }

        Err(ProviderError::Http(
            status.as_u16(),
            format!("Missing HX-Redirect or Location header from {post_url}"),
        ))
    }
}

fn is_direct_download_url(link: &str) -> bool {
    let Ok(url) = url::Url::parse(link) else {
        return false;
    };

    let Some(host) = url.host_str().map(str::to_ascii_lowercase) else {
        return false;
    };

    host == "dl.fuckingfast.co"
        || host.ends_with(".dl.fuckingfast.co")
        || ((host == "fuckingfast.co" || host.ends_with(".fuckingfast.co"))
            && url.path().starts_with("/dl/"))
}

pub(crate) fn extract_file_id(link: &str) -> Option<String> {
    let parsed = url::Url::parse(link).ok()?;
    let host = parsed.host_str()?.to_ascii_lowercase();
    if host != "fuckingfast.co" && !host.ends_with(".fuckingfast.co") {
        return None;
    }
    if host == "dl.fuckingfast.co" || host.ends_with(".dl.fuckingfast.co") {
        return None;
    }

    let segments: Vec<_> = parsed
        .path_segments()?
        .filter(|segment| !segment.is_empty())
        .collect();

    match segments.as_slice() {
        [id] => Some((*id).to_string()),
        ["f", id] | ["f", id, "go"] => Some((*id).to_string()),
        _ => None,
    }
}

pub(crate) fn normalize_redirect_url(base: &str, redirect: &str) -> Result<String, ProviderError> {
    let redirect = redirect.trim();
    if redirect.is_empty() {
        return Err(ProviderError::Parse("Empty FuckingFast redirect".into()));
    }

    if redirect.starts_with('{') {
        let value = serde_json::from_str::<serde_json::Value>(redirect)
            .map_err(|error| ProviderError::Parse(format!("Invalid HX-Location JSON: {error}")))?;
        if let Some(path) = value.get("path").and_then(|path| path.as_str()) {
            return normalize_redirect_url(base, path);
        }
    }

    if let Ok(url) = url::Url::parse(redirect) {
        return Ok(url.to_string());
    }

    let base = url::Url::parse(base)
        .map_err(|_| ProviderError::Parse(format!("Invalid redirect base: {base}")))?;
    base.join(redirect)
        .map(|url| url.to_string())
        .map_err(|error| ProviderError::Parse(format!("Invalid redirect URL: {error}")))
}

pub(crate) fn extract_direct_download_url(body: &str) -> Option<String> {
    let normalized = body.replace(r"\/", "/").replace("&amp;", "&");
    let re = Regex::new(r#"https?://(?:dl\.fuckingfast\.co|fuckingfast\.co/dl)/[^\s"'<>\\]+"#)
        .ok()?;
    re.find(&normalized).map(|m| m.as_str().to_string())
}

fn is_rate_limited_body(body: &str) -> bool {
    let lower = body.to_ascii_lowercase();
    lower.contains("rate limited")
        || lower.contains("rate limit")
        || lower.contains("too many requests")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_file_id_from_share_url() {
        assert_eq!(
            extract_file_id("https://fuckingfast.co/abc123?download=1#frag"),
            Some("abc123".to_string())
        );
    }

    #[test]
    fn extracts_file_id_from_user_sample_urls() {
        assert_eq!(
            extract_file_id(
                "https://fuckingfast.co/rwhe4g1lwtqe#LIFTED_--*fitgirl-repacks.site*--_.part1.rar"
            ),
            Some("rwhe4g1lwtqe".to_string())
        );
        assert_eq!(
            extract_file_id(
                "https://fuckingfast.co/1e9i2l04sf68#LIFTED_--*fitgirl-repacks.site*--_.part2.rar"
            ),
            Some("1e9i2l04sf68".to_string())
        );
        assert_eq!(
            extract_file_id(
                "https://fuckingfast.co/c7cdq0xald3y#LIFTED_--*fitgirl-repacks.site*--_.part3.rar"
            ),
            Some("c7cdq0xald3y".to_string())
        );
    }

    #[test]
    fn extracts_file_id_from_go_url() {
        assert_eq!(
            extract_file_id("https://fuckingfast.co/f/abc123/go"),
            Some("abc123".to_string())
        );
    }

    #[test]
    fn ignores_direct_download_host_for_file_id() {
        assert_eq!(extract_file_id("https://dl.fuckingfast.co/file.bin"), None);
    }

    #[test]
    fn normalizes_relative_redirects() {
        assert_eq!(
            normalize_redirect_url("https://fuckingfast.co/abc123", "/dl/file.bin").unwrap(),
            "https://fuckingfast.co/dl/file.bin"
        );
    }

    #[test]
    fn extracts_direct_download_from_body() {
        let body =
            r#"<a href="https://dl.fuckingfast.co/files/game.part01.rar?token=1">Download</a>"#;
        assert_eq!(
            extract_direct_download_url(body),
            Some("https://dl.fuckingfast.co/files/game.part01.rar?token=1".to_string())
        );
    }
}
