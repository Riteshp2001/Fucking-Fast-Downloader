use crate::error::AppError;
use regex::Regex;
use reqwest::header::{HeaderMap, HeaderValue, REFERER};
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;
use url::Url;

// ─── Regex patterns (compiled once, reused) ───────────────────────────────────

/// Matches the direct download URL embedded in the page JavaScript:
///   window.open("https://fuckingfast.co/dl/...")
static FF_DL_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"window\.open\(\s*["'](https?://[^"']*fuckingfast\.[^"']*?/dl/[^"']*)["']\s*\)"#)
        .expect("FF_DL_REGEX compile")
});

/// Fallback: direct href to /dl/ path
static FF_DL_HREF_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"href\s*=\s*["'](https?://[^"']*fuckingfast\.[^"']*?/dl/[^"']*)["']"#)
        .expect("FF_DL_HREF_REGEX compile")
});

/// Extracts file size from page text, e.g. "Size: 1.23 GB"
static FF_SIZE_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)Size:\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)"#)
        .expect("FF_SIZE_REGEX compile")
});

// ─── Data structures ──────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct ScrapeResult {
    pub original_url: String,
    pub file_links: Vec<String>,
    pub resolved_links: Vec<ResolvedLink>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ResolvedLink {
    pub original: String,
    pub direct_url: Option<String>,
    pub file_id: String,
    pub file_name: Option<String>,
    pub source_name: Option<String>,
    pub file_size: Option<String>,
    pub success: bool,
    pub error: Option<String>,
}

// ─── HTTP client builder ──────────────────────────────────────────────────────

fn build_client() -> Result<reqwest::Client, AppError> {
    let mut headers = HeaderMap::new();
    headers.insert(REFERER, HeaderValue::from_static("https://fitgirl-repacks.site/"));
    headers.insert("accept-language", HeaderValue::from_static("en-US,en;q=0.9"));
    // Chrome-like sec-ch-ua hints to pass TLS/header fingerprint checks
    headers.insert("sec-ch-ua", HeaderValue::from_static(
        r#""Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24""#,
    ));
    headers.insert("sec-ch-ua-mobile", HeaderValue::from_static("?0"));
    headers.insert("sec-ch-ua-platform", HeaderValue::from_static("\"Windows\""));
    headers.insert("dnt", HeaderValue::from_static("1"));

    reqwest::Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        .default_headers(headers)
        .cookie_store(true)
        // Use rustls which has a more browser-like TLS fingerprint than native-tls
        .use_rustls_tls()
        // Follow redirects automatically (Cloudflare may 302 before serving content)
        .redirect(reqwest::redirect::Policy::limited(10))
        // Accept compressed responses
        .gzip(true)
        .brotli(true)
        .deflate(true)
        .build()
        .map_err(|e| AppError::Engine(format!("Failed to build HTTP client: {e}")))
}

// ─── URL validation ───────────────────────────────────────────────────────────

fn validated_url(value: &str, expected_host: &str) -> Result<Url, AppError> {
    let parsed = Url::parse(value.trim())
        .map_err(|_| AppError::Engine("Please enter a valid HTTPS URL.".into()))?;
    let host = parsed.host_str().unwrap_or_default().to_ascii_lowercase();

    if parsed.scheme() != "https"
        || (host != expected_host && host != format!("www.{expected_host}"))
    {
        return Err(AppError::Engine(format!("URL must belong to {expected_host}.")));
    }

    Ok(parsed)
}

// ─── Page fetching with retry ─────────────────────────────────────────────────

/// Fetch a page with retry logic and exponential backoff.
/// Handles transient Cloudflare 403/5xx errors by retrying up to `max_retries` times.
async fn fetch_page_with_retry(
    client: &reqwest::Client,
    url: &str,
    max_retries: u32,
) -> Result<String, AppError> {
    let mut last_error = String::new();

    for attempt in 0..=max_retries {
        if attempt > 0 {
            // Exponential backoff: 1s, 2s, 4s
            let delay = std::time::Duration::from_millis(1000 * 2u64.pow(attempt - 1));
            tokio::time::sleep(delay).await;
            log::info!("Retry attempt {attempt}/{max_retries} for {url}");
        }

        match fetch_page(client, url).await {
            Ok(html) => return Ok(html),
            Err(e) => {
                last_error = e.to_string();
                let is_retryable = last_error.contains("403")
                    || last_error.contains("429")
                    || last_error.contains("500")
                    || last_error.contains("502")
                    || last_error.contains("503")
                    || last_error.contains("504")
                    || last_error.contains("timeout")
                    || last_error.contains("connection");

                if !is_retryable || attempt == max_retries {
                    return Err(AppError::Engine(format!(
                        "Failed after {} attempt(s): {}",
                        attempt + 1,
                        last_error
                    )));
                }
            }
        }
    }

    Err(AppError::Engine(last_error))
}

async fn fetch_page(client: &reqwest::Client, url: &str) -> Result<String, AppError> {
    let resp = client
        .get(url)
        .header(
            "accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        )
        .header("sec-fetch-dest", "document")
        .header("sec-fetch-mode", "navigate")
        .header("sec-fetch-site", "none")
        .header("sec-fetch-user", "?1")
        .header("upgrade-insecure-requests", "1")
        .header("cache-control", "max-age=0")
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| AppError::Engine(format!("Network error: {e}")))?;

    let status = resp.status();
    if !status.is_success() {
        return Err(AppError::Engine(format!("HTTP {status}")));
    }

    resp.text()
        .await
        .map_err(|e| AppError::Engine(format!("Failed to read body: {e}")))
}

// ─── FitGirl page scraping ────────────────────────────────────────────────────

fn extract_slug_from_url(url: &str) -> Option<String> {
    let trimmed = url.trim_end_matches('/');
    trimmed
        .split('/')
        .last()
        .map(|s| s.to_string())
        .filter(|s| !s.is_empty())
}

/// Scrape a FitGirl repack page for FuckingFast download links.
/// Searches multiple selectors to maximize link discovery.
#[tauri::command]
pub async fn scrape_fitgirl_page(url: String) -> Result<ScrapeResult, AppError> {
    let page_url = validated_url(&url, "fitgirl-repacks.site")?;
    let client = build_client()?;

    let html = fetch_page_with_retry(&client, page_url.as_str(), 3).await?;
    let document = Html::parse_document(&html);

    let mut ff_links: Vec<String> = Vec::new();
    let mut seen = std::collections::HashSet::new();

    // Strategy 1: Look in div.dlinks (primary download section)
    if let Ok(dlinks_sel) = Selector::parse("div.dlinks") {
        if let Ok(link_sel) = Selector::parse("a[href]") {
            for dlinks_div in document.select(&dlinks_sel) {
                for a in dlinks_div.select(&link_sel) {
                    if let Some(href) = a.value().attr("href") {
                        try_add_ff_link(href, &mut ff_links, &mut seen);
                    }
                }
            }
        }
    }

    // Strategy 2: Look in .entry-content li > a (some pages use list format)
    if let Ok(entry_sel) = Selector::parse(".entry-content li a[href]") {
        for a in document.select(&entry_sel) {
            if let Some(href) = a.value().attr("href") {
                try_add_ff_link(href, &mut ff_links, &mut seen);
            }
        }
    }

    // Strategy 3: Look in ALL .entry-content links as last resort
    if ff_links.is_empty() {
        if let Ok(all_links_sel) = Selector::parse(".entry-content a[href]") {
            for a in document.select(&all_links_sel) {
                if let Some(href) = a.value().attr("href") {
                    try_add_ff_link(href, &mut ff_links, &mut seen);
                }
            }
        }
    }

    Ok(ScrapeResult {
        original_url: url,
        file_links: ff_links,
        resolved_links: Vec::new(),
    })
}

fn try_add_ff_link(href: &str, ff_links: &mut Vec<String>, seen: &mut std::collections::HashSet<String>) {
    let h = href.trim();
    // Accept both fuckingfast.co and fuckingfast.net links
    if let Ok(parsed) = Url::parse(h) {
        let host = parsed.host_str().unwrap_or_default().to_ascii_lowercase();
        if host.contains("fuckingfast") {
            let normalized = parsed.as_str().to_string();
            if seen.insert(normalized.clone()) {
                ff_links.push(normalized);
            }
        }
    }
}

// ─── FuckingFast link resolution ──────────────────────────────────────────────

/// Extracts the download URL from a FuckingFast page using regex patterns.
/// Primary: window.open("https://fuckingfast.co/dl/...")
/// Fallback: href="https://fuckingfast.co/dl/..."
/// Last resort: hx-post button approach
fn extract_download_url(html: &str) -> Option<String> {
    // Primary: window.open() pattern (most reliable, used by Fit-Launcher)
    if let Some(caps) = FF_DL_REGEX.captures(html) {
        if let Some(url) = caps.get(1) {
            return Some(url.as_str().to_string());
        }
    }

    // Fallback: href to /dl/ path
    if let Some(caps) = FF_DL_HREF_REGEX.captures(html) {
        if let Some(url) = caps.get(1) {
            return Some(url.as_str().to_string());
        }
    }

    None
}

/// Extracts file size text from the page, e.g. "1.23 GB"
fn extract_file_size(html: &str) -> Option<String> {
    FF_SIZE_REGEX.captures(html).map(|caps| {
        let num = caps.get(1).map(|m| m.as_str()).unwrap_or("?");
        let unit = caps.get(2).map(|m| m.as_str()).unwrap_or("");
        format!("{num} {unit}")
    })
}

/// Extracts the `hx-post` path from the download button (legacy fallback)
fn find_hx_post(html: &str) -> Option<String> {
    let document = Html::parse_document(html);
    // Try multiple selector patterns
    let selectors = [
        "a.link-button[hx-post]",
        "button[hx-post]",
        "[hx-post]",
    ];
    for sel_str in selectors {
        if let Ok(selector) = Selector::parse(sel_str) {
            if let Some(el) = document.select(&selector).next() {
                if let Some(path) = el.value().attr("hx-post") {
                    return Some(path.to_string());
                }
            }
        }
    }
    None
}

fn find_meta_title(html: &str) -> Option<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("meta[name='title']").ok()?;
    document
        .select(&selector)
        .next()?
        .value()
        .attr("content")
        .map(|s| s.to_string())
}

fn find_file_name(html: &str) -> Option<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("h1.entry-title, h1.post-title, title").ok()?;
    for el in document.select(&selector) {
        let text: String = el.text().collect();
        let trimmed = text.trim().to_string();
        if !trimmed.is_empty() {
            return Some(trimmed);
        }
    }
    None
}

#[tauri::command]
pub async fn resolve_fuckingfast_link(link: String) -> Result<ResolvedLink, AppError> {
    // Validate URL — accept both fuckingfast.co and fuckingfast.net
    let parsed_link = match Url::parse(link.trim()) {
        Ok(url) => {
            let host = url.host_str().unwrap_or_default().to_ascii_lowercase();
            if !host.contains("fuckingfast") {
                return Ok(ResolvedLink {
                    original: link,
                    direct_url: None,
                    file_id: String::new(),
                    file_name: None,
                    source_name: None,
                    file_size: None,
                    success: false,
                    error: Some("URL must belong to fuckingfast.co or fuckingfast.net".into()),
                });
            }
            url
        }
        Err(_) => {
            return Ok(ResolvedLink {
                original: link,
                direct_url: None,
                file_id: String::new(),
                file_name: None,
                source_name: None,
                file_size: None,
                success: false,
                error: Some("Invalid URL".into()),
            });
        }
    };

    let link = parsed_link.as_str().to_string();
    let file_id = extract_slug_from_url(&link).unwrap_or_default();
    if file_id.is_empty() {
        return Ok(ResolvedLink {
            original: link,
            direct_url: None,
            file_id: String::new(),
            file_name: None,
            source_name: None,
            file_size: None,
            success: false,
            error: Some("Could not extract file_id from link".into()),
        });
    }

    let client = build_client()?;

    // Fetch the FuckingFast landing page with retry
    let page_html = match fetch_page_with_retry(&client, &link, 2).await {
        Ok(h) => h,
        Err(e) => {
            return Ok(ResolvedLink {
                original: link,
                direct_url: None,
                file_id,
                file_name: None,
                source_name: None,
                file_size: None,
                success: false,
                error: Some(e.to_string()),
            });
        }
    };

    let file_name = find_meta_title(&page_html);
    let source_name = find_file_name(&page_html);
    let file_size = extract_file_size(&page_html);

    // ── Strategy 1: Regex extraction (primary — most reliable) ──────────
    if let Some(dl_url) = extract_download_url(&page_html) {
        return Ok(ResolvedLink {
            original: link,
            direct_url: Some(dl_url),
            file_id,
            file_name,
            source_name,
            file_size,
            success: true,
            error: None,
        });
    }

    // ── Strategy 2: hx-post fallback ────────────────────────────────────
    if let Some(hx_post_path) = find_hx_post(&page_html) {
        let go_url = if hx_post_path.starts_with("http") {
            hx_post_path.clone()
        } else if hx_post_path.starts_with('/') {
            format!("https://fuckingfast.co{hx_post_path}")
        } else {
            format!("https://fuckingfast.co/{hx_post_path}")
        };

        let post_resp = client
            .post(&go_url)
            .header("accept", "*/*")
            .header("content-type", "application/x-www-form-urlencoded")
            .header("hx-request", "true")
            .header("hx-current-url", &link)
            .header("origin", "https://fuckingfast.co")
            .header("referer", &link)
            .timeout(std::time::Duration::from_secs(15))
            .send()
            .await
            .map_err(|e| AppError::Engine(format!("POST to {go_url} failed: {e}")))?;

        // Check response body for a redirect URL
        let resp_body = post_resp
            .text()
            .await
            .unwrap_or_default();

        // Try to extract from the POST response body too
        if let Some(dl_url) = extract_download_url(&resp_body) {
            return Ok(ResolvedLink {
                original: link,
                direct_url: Some(dl_url),
                file_id,
                file_name,
                source_name,
                file_size,
                success: true,
                error: None,
            });
        }
    }

    // ── All strategies failed ───────────────────────────────────────────
    Ok(ResolvedLink {
        original: link,
        direct_url: None,
        file_id,
        file_name,
        source_name,
        file_size,
        success: false,
        error: Some(
            "Could not extract download URL. The site may have updated its protection. Try again or use a browser.".into(),
        ),
    })
}

// ─── Combined scrape + resolve ────────────────────────────────────────────────

#[tauri::command]
pub async fn scrape_and_resolve(url: String) -> Result<ScrapeResult, AppError> {
    let mut result = scrape_fitgirl_page(url).await?;

    let mut resolved = Vec::new();
    for link in &result.file_links {
        match resolve_fuckingfast_link(link.clone()).await {
            Ok(r) => resolved.push(r),
            Err(e) => resolved.push(ResolvedLink {
                original: link.clone(),
                direct_url: None,
                file_id: String::new(),
                file_name: None,
                source_name: None,
                file_size: None,
                success: false,
                error: Some(e.to_string()),
            }),
        }
    }

    result.resolved_links = resolved;
    Ok(result)
}
