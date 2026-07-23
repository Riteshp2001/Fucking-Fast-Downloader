use crate::error::AppError;
use reqwest::header::{HeaderMap, HeaderValue, REFERER};
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use url::Url;

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
    pub success: bool,
    pub error: Option<String>,
}

fn build_client() -> Result<reqwest::Client, AppError> {
    let mut headers = HeaderMap::new();
    headers.insert(REFERER, HeaderValue::from_static("https://fitgirl-repacks.site/"));
    headers.insert("accept-language", HeaderValue::from_static("en-US,en;q=0.9"));

    reqwest::Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        .default_headers(headers)
        .cookie_store(true)
        .build()
        .map_err(|e| AppError::Engine(format!("Failed to build HTTP client: {e}")))
}

fn validated_url(value: &str, expected_host: &str) -> Result<Url, AppError> {
    let parsed = Url::parse(value.trim())
        .map_err(|_| AppError::Engine("Please enter a valid HTTPS URL.".into()))?;
    let host = parsed.host_str().unwrap_or_default().to_ascii_lowercase();

    if parsed.scheme() != "https" || (host != expected_host && host != format!("www.{expected_host}")) {
        return Err(AppError::Engine(format!("URL must belong to {expected_host}.")));
    }

    Ok(parsed)
}

#[tauri::command]
pub async fn scrape_fitgirl_page(url: String) -> Result<ScrapeResult, AppError> {
    let page_url = validated_url(&url, "fitgirl-repacks.site")?;
    let client = build_client()?;

    let html = fetch_page(&client, page_url.as_str()).await?;
    let document = Html::parse_document(&html);
    let dlinks_selector = Selector::parse("div.dlinks").unwrap();
    let link_selector = Selector::parse("a[href]").unwrap();

    let mut ff_links: Vec<String> = Vec::new();
    let mut seen = std::collections::HashSet::new();

    for dlinks_div in document.select(&dlinks_selector) {
        for a in dlinks_div.select(&link_selector) {
            if let Some(href) = a.value().attr("href") {
                let h = href.trim();
                if let Ok(parsed) = validated_url(h, "fuckingfast.co") {
                    let normalized = parsed.as_str().to_string();
                    if seen.insert(normalized.clone()) {
                        ff_links.push(normalized);
                    }
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

async fn fetch_page(client: &reqwest::Client, url: &str) -> Result<String, AppError> {
    let resp = client
        .get(url)
        .header("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8")
        .header("sec-fetch-dest", "document")
        .header("sec-fetch-mode", "navigate")
        .header("sec-fetch-site", "none")
        .header("sec-fetch-user", "?1")
        .header("upgrade-insecure-requests", "1")
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| AppError::Engine(format!("Failed to fetch page: {e}")))?;

    if !resp.status().is_success() {
        return Err(AppError::Engine(format!("HTTP {}", resp.status())));
    }

    resp.text()
        .await
        .map_err(|e| AppError::Engine(format!("Failed to read body: {e}")))
}

fn extract_slug_from_url(url: &str) -> Option<String> {
    let trimmed = url.trim_end_matches('/');
    trimmed.split('/').last().map(|s| s.to_string()).filter(|s| !s.is_empty())
}

/// Extracts the `hx-post` path from the download button on the fuckingfast page
fn find_hx_post(html: &str) -> Option<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("a.link-button[hx-post]").ok()?;
    document.select(&selector).next()?.value().attr("hx-post").map(|s| s.to_string())
}

fn find_meta_title(html: &str) -> Option<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("meta[name='title']").ok()?;
    document.select(&selector).next()?.value().attr("content").map(|s| s.to_string())
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
    let parsed_link = match validated_url(&link, "fuckingfast.co") {
        Ok(url) => url,
        Err(error) => {
            return Ok(ResolvedLink {
                original: link,
                direct_url: None,
                file_id: String::new(),
                file_name: None,
                source_name: None,
                success: false,
                error: Some(error.to_string()),
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
            success: false,
            error: Some("Could not extract file_id from link".into()),
        });
    }

    let client = build_client()?;

    let page_html = match fetch_page(&client, &link).await {
        Ok(h) => h,
        Err(e) => {
            return Ok(ResolvedLink {
                original: link,
                direct_url: None,
                file_id,
                file_name: None,
                source_name: None,
                success: false,
                error: Some(e.to_string()),
            });
        }
    };

    let file_name = find_meta_title(&page_html);
    let source_name = find_file_name(&page_html);
    let hx_post_path = find_hx_post(&page_html);

    let hx_post_path = match hx_post_path {
        Some(p) => p,
        None => {
            return Ok(ResolvedLink {
                original: link,
                direct_url: None,
                file_id,
                file_name,
                source_name,
                success: false,
                error: Some("Download button (a.link-button[hx-post]) not found on page".into()),
            });
        }
    };

    // hx-post is a relative path like "/f/abc123/go"
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

    let direct_url = post_resp
        .headers()
        .get("hx-redirect")
        .or_else(|| post_resp.headers().get("HX-Redirect"))
        .or_else(|| post_resp.headers().get(reqwest::header::LOCATION))
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string())
        .filter(|url| Url::parse(url).is_ok_and(|parsed| matches!(parsed.scheme(), "http" | "https")));

    match direct_url {
        Some(url) => Ok(ResolvedLink {
            original: link,
            direct_url: Some(url),
            file_id,
            file_name,
            source_name,
            success: true,
            error: None,
        }),
        None => Ok(ResolvedLink {
            original: link,
            direct_url: None,
            file_id,
            file_name,
            source_name,
            success: false,
            error: Some(format!(
                "No HX-Redirect header in POST response (HTTP {})",
                post_resp.status()
            )),
        }),
    }
}

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
                success: false,
                error: Some(e.to_string()),
            }),
        }
    }

    result.resolved_links = resolved;
    Ok(result)
}
