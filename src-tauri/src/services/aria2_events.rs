//! Aria2 WebSocket event bridge.
//!
//! HTTP JSON-RPC is request/response only.  The WebSocket endpoint emits
//! download notifications immediately, so the frontend can react without a
//! fixed polling delay.

use crate::aria2::client::Aria2Client;
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use std::sync::Arc;
use tauri::Emitter;
use tokio::sync::watch;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::Message;
use tokio_tungstenite::MaybeTlsStream;
use tokio_tungstenite::WebSocketStream;

pub const DOWNLOAD_COMPLETE: &str = "aria2-event:download-complete";

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DownloadCompleteEvent {
    pub gid: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
struct Aria2EventGid {
    gid: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
struct Aria2Notification {
    method: String,
    #[serde(default)]
    params: Vec<Aria2EventGid>,
}

pub struct Aria2EventHandle {
    stop_tx: watch::Sender<bool>,
}

impl Aria2EventHandle {
    pub fn stop(&self) {
        let _ = self.stop_tx.send(true);
    }
}

pub struct Aria2EventState(pub Arc<tokio::sync::Mutex<Option<Aria2EventHandle>>>);

impl Aria2EventState {
    pub fn new() -> Self {
        Self(Arc::new(tokio::sync::Mutex::new(None)))
    }
}

pub fn spawn_aria2_event_listener(
    app: tauri::AppHandle,
    aria2: Arc<Aria2Client>,
) -> Aria2EventHandle {
    let (stop_tx, stop_rx) = watch::channel(false);
    tokio::spawn(async move {
        event_loop(app, aria2, stop_rx).await;
    });
    Aria2EventHandle { stop_tx }
}

async fn event_loop(
    app: tauri::AppHandle,
    aria2: Arc<Aria2Client>,
    mut stop_rx: watch::Receiver<bool>,
) {
    let (port, secret) = aria2.credentials().await;
    let url = format!("ws://127.0.0.1:{port}/jsonrpc");
    let Ok((mut socket, _)) = connect_async(&url).await else {
        log::warn!("aria2_events: failed to connect websocket");
        return;
    };

    if let Err(e) = authorize_socket(&mut socket, &secret).await {
        log::warn!("aria2_events: websocket authorization failed: {e}");
        return;
    }

    log::info!("aria2_events: websocket listening");

    loop {
        tokio::select! {
            _ = stop_rx.changed() => {
                if *stop_rx.borrow() {
                    log::info!("aria2_events: stopped");
                    let _ = socket.close(None).await;
                    return;
                }
            }
            msg = socket.next() => {
                let Some(Ok(message)) = msg else {
                    log::debug!("aria2_events: websocket closed");
                    return;
                };
                if let Some(gid) = completed_gid_from_message(&message) {
                    let payload = DownloadCompleteEvent { gid };
                    if let Err(e) = app.emit(DOWNLOAD_COMPLETE, payload) {
                        log::warn!("aria2_events: failed to emit download completion: {e}");
                    }
                }
            }
        }
    }
}

async fn authorize_socket(
    socket: &mut WebSocketStream<MaybeTlsStream<tokio::net::TcpStream>>,
    secret: &str,
) -> Result<(), tokio_tungstenite::tungstenite::Error> {
    let params = if secret.is_empty() {
        Vec::new()
    } else {
        vec![serde_json::json!(format!("token:{secret}"))]
    };
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": "ff-downloader-events-auth",
        "method": "aria2.getVersion",
        "params": params,
    });
    socket.send(Message::Text(request.to_string().into())).await
}

fn completed_gid_from_message(message: &Message) -> Option<String> {
    let Message::Text(text) = message else {
        return None;
    };
    completed_gid_from_text(text)
}

fn completed_gid_from_text(text: &str) -> Option<String> {
    let notification: Aria2Notification = serde_json::from_str(text).ok()?;
    if notification.method != "aria2.onDownloadComplete" {
        return None;
    }
    notification
        .params
        .first()
        .map(|payload| payload.gid.clone())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn completed_gid_from_text_extracts_on_download_complete_gid() {
        let gid = completed_gid_from_text(
            r#"{"jsonrpc":"2.0","method":"aria2.onDownloadComplete","params":[{"gid":"abc123"}]}"#,
        );

        assert_eq!(gid.as_deref(), Some("abc123"));
    }

    #[test]
    fn completed_gid_from_text_ignores_non_completion_events() {
        let gid = completed_gid_from_text(
            r#"{"jsonrpc":"2.0","method":"aria2.onDownloadStart","params":[{"gid":"abc123"}]}"#,
        );

        assert_eq!(gid, None);
    }

    #[test]
    fn completed_gid_from_text_ignores_rpc_responses() {
        let gid = completed_gid_from_text(
            r#"{"jsonrpc":"2.0","id":"ff-downloader-events-auth","result":{"version":"1.37.0"}}"#,
        );

        assert_eq!(gid, None);
    }

    #[test]
    fn completed_gid_from_text_handles_empty_params() {
        let gid = completed_gid_from_text(
            r#"{"jsonrpc":"2.0","method":"aria2.onDownloadComplete","params":[]}"#,
        );

        assert_eq!(gid, None);
    }
}
