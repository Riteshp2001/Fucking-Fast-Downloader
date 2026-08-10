use crate::providers::error::ProviderError;
use regex::Regex;
use reqwest::{header, Client};
use std::time::Duration;
use tauri::Manager;

const BASE_URL: &str = "https://fuckingfast.co";
const MAX_RETRIES: u32 = 3;
const WEBVIEW_TIMEOUT: Duration = Duration::from_secs(60);

pub struct FuckingFastResolver {
    client: Client,
    app_handle: Option<tauri::AppHandle>,
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

        Self {
            client,
            app_handle: None,
        }
    }

    #[allow(dead_code)]
    pub fn with_app_handle(mut self, app_handle: tauri::AppHandle) -> Self {
        self.app_handle = Some(app_handle);
        self
    }

    pub async fn resolve(&self, link: &str) -> Result<String, ProviderError> {
        if is_direct_download_url(link) {
            return Ok(link.to_string());
        }

        let file_id = extract_file_id(link)
            .ok_or_else(|| ProviderError::Parse(format!("Invalid FuckingFast link: {link}")))?;
        let clean_url = format!("{BASE_URL}/{file_id}");
        let post_url = format!("{BASE_URL}/f/{file_id}/go");
        let mut errors = Vec::new();

        // Match the rendered-page path first. FuckingFast often opens a signed
        // URL on a CDN whose hostname is unrelated to fuckingfast.co.
        match self.fetch_page_direct_url(&clean_url).await {
            Ok(Some(url)) => return Ok(url),
            Ok(None) => {}
            Err(error) => errors.push(error),
        }

        // Newer layouts can expose an HTMX POST endpoint instead.
        match self.post_go(&post_url, &clean_url).await {
            Ok(url) => return Ok(url),
            Err(error) => errors.push(error),
        }

        for attempt in 0..MAX_RETRIES {
            if attempt > 0 {
                tokio::time::sleep(Duration::from_secs(2 * attempt as u64)).await;
            }

            match self.fetch_page_direct_url(&clean_url).await {
                Ok(Some(url)) => return Ok(url),
                Ok(None) => {}
                Err(error) => errors.push(error),
            }

            match self.post_go(&post_url, &clean_url).await {
                Ok(url) => return Ok(url),
                Err(error) => errors.push(error),
            }
        }

        // Last resort: let the system WebView solve browser challenges. The
        // window.open override turns popup navigation into same-window navigation
        // so on_page_load can capture any signed HTTP(S) CDN destination.
        if let Some(app_handle) = &self.app_handle {
            match self.resolve_via_webview(app_handle, &clean_url).await {
                Ok(url) => return Ok(url),
                Err(error) => errors.push(error),
            }
        }

        Err(errors
            .pop()
            .unwrap_or(ProviderError::Network("FuckingFast resolve failed".into())))
    }

    async fn fetch_page_direct_url(
        &self,
        clean_url: &str,
    ) -> Result<Option<String>, ProviderError> {
        let resp = self
            .client
            .get(clean_url)
            .header(
                header::ACCEPT,
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            )
            .header(header::ACCEPT_LANGUAGE, "en-US,en;q=0.9")
            .header(header::CACHE_CONTROL, "no-cache")
            .header(header::PRAGMA, "no-cache")
            .header(header::UPGRADE_INSECURE_REQUESTS, "1")
            .header("Sec-Fetch-Dest", "document")
            .header("Sec-Fetch-Mode", "navigate")
            .header("Sec-Fetch-Site", "cross-site")
            .send()
            .await?;

        let status = resp.status();
        let reason = status.canonical_reason().unwrap_or("Unknown").to_string();
        let body = resp.text().await.map_err(ProviderError::from)?;

        if let Some(url) = extract_download_candidate(&body) {
            return Ok(Some(url));
        }

        if is_rate_limited_body(&body) {
            return Err(ProviderError::Http(
                429,
                "FuckingFast rate limit detected; wait a few minutes and retry".into(),
            ));
        }

        if is_cloudflare_challenge(&body) {
            return Err(ProviderError::Http(
                status.as_u16(),
                format!(
                    "Cloudflare protection detected on {clean_url}. Browser resolution is required."
                ),
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
            .and_then(|value| normalize_redirect_url(clean_url, value).ok())
            .and_then(|value| validate_http_download_url(&value).ok());

        if let Some(url) = header_redirect {
            return Ok(url);
        }

        let body = resp.text().await.map_err(ProviderError::from)?;
        if let Some(url) = extract_download_candidate(&body) {
            return Ok(url);
        }

        if status == 403 || status == 429 {
            let lower = body.to_ascii_lowercase();
            if lower.contains("cloudflare")
                || lower.contains("challenge")
                || lower.contains("cf-ray")
            {
                return Err(ProviderError::Http(
                    status.as_u16(),
                    format!(
                        "Cloudflare protection detected on {post_url}. Browser resolution is required."
                    ),
                ));
            }
        }

        Err(ProviderError::Http(
            status.as_u16(),
            format!(
                "FuckingFast did not expose a download target from {post_url}. Status: {status}. Body preview: {}",
                &body[..body.len().min(200)]
            ),
        ))
    }

    async fn resolve_via_webview(
        &self,
        app_handle: &tauri::AppHandle,
        clean_url: &str,
    ) -> Result<String, ProviderError> {
        use std::sync::{Arc, Mutex};
        use std::time::Instant;
        use tauri::WebviewWindowBuilder;

        let result = Arc::new(Mutex::new(None::<Result<String, ProviderError>>));
        let result_clone = result.clone();
        let url = clean_url.to_string();

        if let Some(existing) = app_handle.get_webview_window("ff-resolver") {
            let _ = existing.close();
        }

        let window = WebviewWindowBuilder::new(
            app_handle,
            "ff-resolver",
            tauri::WebviewUrl::External(url.parse().map_err(|error| {
                ProviderError::Parse(format!("Invalid FuckingFast URL: {error}"))
            })?),
        )
        .title("Resolving FuckingFast link...")
        .inner_size(900.0, 700.0)
        .resizable(true)
        .visible(true)
        .decorations(true)
        .on_page_load(move |window, event| {
            if !matches!(event.event(), tauri::webview::PageLoadEvent::Finished) {
                return;
            }

            let Ok(current_url) = window.url() else {
                return;
            };
            let current = current_url.as_str().to_string();

            if is_resolved_navigation_url(&current) {
                if let Ok(mut guard) = result_clone.lock() {
                    *guard = Some(Ok(current));
                }
                let _ = window.close();
                return;
            }

            if is_fuckingfast_page_url(&current) {
                let _ = window.eval(
                    r#"
                    (function () {
                      if (window.__ffResolverInstalled) return;
                      window.__ffResolverInstalled = true;

                      var originalOpen = window.open;
                      window.open = function (target) {
                        if (typeof target === 'string' && /^https?:\/\//i.test(target)) {
                          window.location.assign(target);
                          return null;
                        }
                        if (originalOpen) return originalOpen.apply(window, arguments);
                        return null;
                      };

                      setTimeout(function () {
                        var button = document.querySelector('[hx-post]')
                          || document.querySelector('#download-btn')
                          || document.querySelector('button[type="submit"]')
                          || document.querySelector('.btn.download')
                          || Array.from(document.querySelectorAll('button,a')).find(function (el) {
                               return /download/i.test((el.textContent || '').trim());
                             });
                        if (button && typeof button.click === 'function') button.click();
                      }, 1200);
                    })();
                    "#,
                );
            }
        })
        .build()
        .map_err(|error| ProviderError::Network(format!("Failed to create WebView: {error}")))?;

        let start = Instant::now();
        loop {
            if start.elapsed() > WEBVIEW_TIMEOUT {
                let _ = window.close();
                return Err(ProviderError::Http(
                    408,
                    "FuckingFast browser resolution timed out".into(),
                ));
            }

            if let Ok(guard) = result.lock() {
                if let Some(res) = guard.as_ref() {
                    return res.clone();
                }
            }

            tokio::time::sleep(Duration::from_millis(500)).await;
        }
    }
}

fn is_fuckingfast_page_url(link: &str) -> bool {
    let Ok(url) = url::Url::parse(link) else {
        return false;
    };
    let Some(host) = url.host_str().map(str::to_ascii_lowercase) else {
        return false;
    };
    host == "fuckingfast.co" || host.ends_with(".fuckingfast.co")
}

fn is_resolved_navigation_url(link: &str) -> bool {
    let Ok(url) = url::Url::parse(link) else {
        return false;
    };
    if !matches!(url.scheme(), "http" | "https") {
        return false;
    }
    if is_direct_download_url(link) {
        return true;
    }
    !is_fuckingfast_page_url(link)
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

fn validate_http_download_url(candidate: &str) -> Result<String, ProviderError> {
    let parsed = url::Url::parse(candidate)
        .map_err(|error| ProviderError::Parse(format!("Invalid download URL: {error}")))?;
    if !matches!(parsed.scheme(), "http" | "https") {
        return Err(ProviderError::Parse(format!(
            "Unsupported download URL scheme: {}",
            parsed.scheme()
        )));
    }
    Ok(parsed.to_string())
}

/// Normalize escaping commonly found when a JavaScript snippet is embedded in
/// JSON, HTML attributes, or another JavaScript string. This intentionally
/// decodes only URL-relevant escapes instead of interpreting arbitrary JS.
fn normalize_embedded_markup(body: &str) -> String {
    body.replace(r"\/", "/")
        .replace(r#"\""#, "\"")
        .replace(r"\'", "'")
        .replace(r"\u0026", "&")
        .replace(r"\u003d", "=")
        .replace(r"\u003f", "?")
        .replace(r"\x26", "&")
        .replace("&amp;", "&")
        .replace("&#038;", "&")
}

pub(crate) fn extract_window_open_url(body: &str) -> Option<String> {
    let normalized = normalize_embedded_markup(body);
    let regex =
        Regex::new(r#"(?is)window\s*\.\s*open\s*\(\s*[\"'](https?://[^\"']+)[\"']"#).ok()?;
    let candidate = regex
        .captures(&normalized)
        .and_then(|captures| captures.get(1))?
        .as_str()
        .trim();
    validate_http_download_url(candidate).ok()
}

pub(crate) fn extract_direct_download_url(body: &str) -> Option<String> {
    let normalized = normalize_embedded_markup(body);
    let regex =
        Regex::new(r#"https?://(?:dl\.fuckingfast\.co|fuckingfast\.co/dl)/[^\s\"'<>\\]+"#).ok()?;
    regex
        .find(&normalized)
        .and_then(|matched| validate_http_download_url(matched.as_str()).ok())
}

fn extract_download_candidate(body: &str) -> Option<String> {
    extract_window_open_url(body).or_else(|| extract_direct_download_url(body))
}

fn is_rate_limited_body(body: &str) -> bool {
    let lower = body.to_ascii_lowercase();
    lower.contains("rate limited")
        || lower.contains("rate limit")
        || lower.contains("too many requests")
}

fn is_cloudflare_challenge(body: &str) -> bool {
    let lower = body.to_ascii_lowercase();
    lower.contains("cf-ray")
        || lower.contains("cloudflare")
        || lower.contains("challenge-platform")
        || lower.contains("attention required! | cloudflare")
        || lower.contains("checking your browser before accessing")
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
                "https://fuckingfast.co/rwhe4g1lwtqe#some-file.part1.rar"
            ),
            Some("rwhe4g1lwtqe".to_string())
        );
        assert_eq!(
            extract_file_id(
                "https://fuckingfast.co/1e9i2l04sf68#some-file.part2.rar"
            ),
            Some("1e9i2l04sf68".to_string())
        );
        assert_eq!(
            extract_file_id(
                "https://fuckingfast.co/c7cdq0xald3y#some-file.part3.rar"
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
            r#"<a href=\"https://dl.fuckingfast.co/files/game.part01.rar?token=1\">Download</a>"#;
        assert_eq!(
            extract_direct_download_url(body),
            Some("https://dl.fuckingfast.co/files/game.part01.rar?token=1".to_string())
        );
    }

    #[test]
    fn extracts_reference_style_window_open_url_on_any_cdn() {
        let body = r#"
            <html><script>noop()</script><script>noop()</script><script>noop()</script>
            <script>window.open('https://cdn-files.example.net/signed/game.part01.rar?token=abc')</script></html>
        "#;
        assert_eq!(
            extract_window_open_url(body),
            Some("https://cdn-files.example.net/signed/game.part01.rar?token=abc".to_string())
        );
    }

    #[test]
    fn extracts_escaped_window_open_url() {
        let body = r#"window.open(\"https:\/\/edge.example.com\/file.rar?x=1\u0026y=2\")"#;
        assert_eq!(
            extract_window_open_url(body),
            Some("https://edge.example.com/file.rar?x=1&y=2".to_string())
        );
    }

    #[test]
    fn extracts_escaped_single_quoted_window_open_url() {
        let body = r#"window.open(\'https:\/\/edge.example.com\/file.rar?x=1\u0026y=2\')"#;
        assert_eq!(
            extract_window_open_url(body),
            Some("https://edge.example.com/file.rar?x=1&y=2".to_string())
        );
    }

    #[test]
    fn rejects_non_http_window_open_targets() {
        let body = r#"window.open('javascript:alert(1)')"#;
        assert_eq!(extract_window_open_url(body), None);
    }

    #[test]
    fn treats_external_https_navigation_as_resolved() {
        assert!(is_resolved_navigation_url(
            "https://storage.example.net/download/file.rar?sig=1"
        ));
        assert!(!is_resolved_navigation_url("https://fuckingfast.co/abc123"));
    }
}
