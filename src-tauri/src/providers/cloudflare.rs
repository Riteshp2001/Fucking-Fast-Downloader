use crate::providers::error::ProviderError;
use reqwest::Response;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tauri::{AppHandle, Listener, Manager, WebviewUrl, WebviewWindowBuilder};
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CloudflareCookies {
    pub cookies: HashMap<String, String>,
    pub domain: String,
}

pub struct CloudflareHandler {
    cookies_path: PathBuf,
    cookies: Arc<Mutex<CloudflareCookies>>,
}

impl CloudflareHandler {
    pub fn new(app_data_dir: &Path) -> Self {
        let cookies_path = app_data_dir.join("cloudflare_cookies.json");
        let cookies = std::fs::read_to_string(&cookies_path)
            .ok()
            .and_then(|s| serde_json::from_str::<CloudflareCookies>(&s).ok())
            .unwrap_or_default();

        Self {
            cookies_path,
            cookies: Arc::new(Mutex::new(cookies)),
        }
    }

    pub fn is_guarded(resp: &Response) -> bool {
        if resp.status().as_u16() != 403 {
            return false;
        }
        resp.headers()
            .get("server")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.to_lowercase().contains("ddos-guard"))
            .unwrap_or(false)
    }

    pub async fn get_cookie_header(&self) -> String {
        let cookies = self.cookies.lock().await;
        cookies
            .cookies
            .iter()
            .map(|(k, v)| format!("{k}={v}"))
            .collect::<Vec<_>>()
            .join("; ")
    }

    pub async fn solve_captcha(
        &self,
        app: &AppHandle,
        url: &str,
    ) -> Result<(), ProviderError> {
        let label = "cloudflare-captcha";

        if let Some(w) = app.get_webview_window(label) {
            let _ = w.close();
        }

        let (tx, rx) = tokio::sync::oneshot::channel::<String>();
        let tx = std::sync::Mutex::new(Some(tx));

        let event_id = app.listen_any("captcha-cookies", move |event| {
            if let Ok(mut tx) = tx.lock() {
                if let Some(tx) = tx.take() {
                    let _ = tx.send(event.payload().to_string());
                }
            }
        });

        let parsed_url = url::Url::parse(url)
            .map_err(|_| ProviderError::Internal("Invalid URL".into()))?;

        let builder = WebviewWindowBuilder::new(app, label, WebviewUrl::External(parsed_url))
            .title("FitGirl - DDoS-Guard Verification")
            .inner_size(800.0, 700.0)
            .resizable(true)
            .center();

        let window = builder
            .build()
            .map_err(|e| ProviderError::Internal(format!("Failed to create captcha window: {e}")))?;

        let js = r#"
            (function() {
                const check = setInterval(() => {
                    const el = document.querySelector('.site-title');
                    if (el && el.textContent.trim().length > 0) {
                        clearInterval(check);
                        try {
                            window.__TAURI_INTERNALS__.emit('captcha-cookies', {
                                cookies: document.cookie,
                                url: location.href
                            });
                        } catch(e) {
                            console.error('captcha: emit failed', e);
                        }
                    }
                }, 500);
            })();
        "#;

        let _ = window.eval(js);

        match tokio::time::timeout(std::time::Duration::from_secs(120), rx).await {
            Ok(Ok(payload)) => {
                if let Ok(parsed) =
                    serde_json::from_str::<serde_json::Value>(&payload)
                {
                    if let Some(cookies_str) = parsed.get("cookies").and_then(|c| c.as_str()) {
                        if !cookies_str.is_empty() {
                            self.update_from_document_cookie(cookies_str, url).await;
                        }
                    }
                }
            }
            _ => {
                if let Some(w) = app.get_webview_window(label) {
                    let _ = w.close();
                }
            }
        }

        app.unlisten(event_id);
        self.persist_cookies().await?;

        Ok(())
    }

    pub async fn update_from_set_cookie(&self, set_cookie: &str, domain: &str) {
        let mut cookies = self.cookies.lock().await;
        cookies.domain = domain.to_string();

        if let Some(eq_pos) = set_cookie.find('=') {
            let name = &set_cookie[..eq_pos];
            let value = if let Some(semi_pos) = set_cookie.find(';') {
                &set_cookie[eq_pos + 1..semi_pos]
            } else {
                &set_cookie[eq_pos + 1..]
            };
            if name.starts_with("__ddg") {
                cookies.cookies.insert(name.to_string(), value.to_string());
            }
        }

        self.persist_inner(&cookies).await;
    }

    async fn update_from_document_cookie(&self, document_cookie: &str, domain: &str) {
        let mut cookies = self.cookies.lock().await;
        cookies.domain = domain.to_string();

        for pair in document_cookie.split(';') {
            let pair = pair.trim();
            if let Some(eq_pos) = pair.find('=') {
                let name = pair[..eq_pos].trim();
                let value = pair[eq_pos + 1..].trim();
                if name.starts_with("__ddg") {
                    cookies
                        .cookies
                        .insert(name.to_string(), value.to_string());
                }
            }
        }

        self.persist_inner(&cookies).await;
    }

    async fn persist_cookies(&self) -> Result<(), ProviderError> {
        let cookies = self.cookies.lock().await;
        self.persist_inner(&cookies).await;
        Ok(())
    }

    async fn persist_inner(&self, cookies: &CloudflareCookies) {
        if let Ok(json) = serde_json::to_string_pretty(cookies) {
            let _ = tokio::fs::write(&self.cookies_path, json).await;
        }
    }
}
