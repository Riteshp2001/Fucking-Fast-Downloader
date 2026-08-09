use crate::aria2::client::Aria2Client;
use crate::aria2::types::Aria2Task;
use crate::error::AppError;
use axum::{
    body::Body,
    extract::{Path as AxumPath, State},
    http::{header, HeaderMap, Response, StatusCode},
    routing::get,
    Router,
};
use std::sync::{Arc, OnceLock};
use std::time::{Duration, Instant};
use tokio::fs::File;
use tokio::io::{AsyncReadExt, AsyncSeekExt, SeekFrom};
use tokio::sync::Mutex;

const STREAM_CHUNK_BYTES: u64 = 4 * 1024 * 1024;
const STREAM_WAIT_TIMEOUT: Duration = Duration::from_secs(20);
const STREAM_POLL_INTERVAL: Duration = Duration::from_millis(250);
const STREAM_PIECE_PRIORITY: &str = "head=64M,tail=32M";

struct TorrentStreamState {
    aria2: Arc<Aria2Client>,
}

struct TorrentStreamServer {
    port: u16,
}

static STREAM_SERVER: OnceLock<Mutex<Option<TorrentStreamServer>>> = OnceLock::new();

fn stream_server() -> &'static Mutex<Option<TorrentStreamServer>> {
    STREAM_SERVER.get_or_init(|| Mutex::new(None))
}

pub async fn prepare_torrent_stream(
    aria2: Arc<Aria2Client>,
    gid: &str,
    file_index: &str,
) -> Result<String, AppError> {
    if gid.is_empty() || !gid.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(AppError::Aria2("Invalid torrent GID".into()));
    }
    let index = file_index
        .parse::<u64>()
        .ok()
        .filter(|index| *index > 0)
        .ok_or_else(|| AppError::Aria2("Invalid torrent file index".into()))?;

    let task = aria2.tell_status(gid).await?;
    if task.bittorrent.is_none() {
        return Err(AppError::Aria2(
            "Streaming is only available for BitTorrent tasks".into(),
        ));
    }
    if !task
        .files
        .iter()
        .any(|file| file.index == index.to_string())
    {
        return Err(AppError::Aria2(format!(
            "Torrent file index {index} does not exist"
        )));
    }

    if task.status != "complete" {
        let options = serde_json::json!({
            "select-file": index.to_string(),
            "bt-prioritize-piece": STREAM_PIECE_PRIORITY,
            "bt-remove-unselected-file": "false"
        });
        aria2.change_option(gid, options).await?;

        if task.status == "paused" {
            aria2.unpause(gid).await?;
        }
    }

    let port = ensure_stream_server(aria2).await?;
    Ok(format!("http://127.0.0.1:{port}/stream/{gid}/{index}"))
}

async fn ensure_stream_server(aria2: Arc<Aria2Client>) -> Result<u16, AppError> {
    let mut guard = stream_server().lock().await;
    if let Some(server) = guard.as_ref() {
        return Ok(server.port);
    }

    let listener = tokio::net::TcpListener::bind(("127.0.0.1", 0))
        .await
        .map_err(|error| AppError::Io(format!("Failed to start torrent stream server: {error}")))?;
    let port = listener
        .local_addr()
        .map_err(|error| AppError::Io(format!("Failed to read torrent stream address: {error}")))?
        .port();

    let state = Arc::new(TorrentStreamState { aria2 });
    let router = Router::new()
        .route("/stream/{gid}/{index}", get(stream_torrent_file))
        .with_state(state);

    tokio::spawn(async move {
        if let Err(error) = axum::serve(listener, router).await {
            log::warn!("torrent_stream: server stopped: {error}");
        }
    });

    *guard = Some(TorrentStreamServer { port });
    log::info!("torrent_stream: listening on 127.0.0.1:{port}");
    Ok(port)
}

async fn stream_torrent_file(
    State(state): State<Arc<TorrentStreamState>>,
    AxumPath((gid, index)): AxumPath<(String, String)>,
    headers: HeaderMap,
) -> Response<Body> {
    if gid.is_empty() || !gid.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return text_response(StatusCode::BAD_REQUEST, "Invalid torrent GID");
    }
    let file_index = match index.parse::<u64>().ok().filter(|value| *value > 0) {
        Some(value) => value,
        None => return text_response(StatusCode::BAD_REQUEST, "Invalid torrent file index"),
    };

    let initial_task = match state.aria2.tell_status(&gid).await {
        Ok(task) => task,
        Err(error) => {
            return text_response(
                StatusCode::BAD_GATEWAY,
                &format!("Could not read torrent status: {error}"),
            )
        }
    };
    if initial_task.bittorrent.is_none() {
        return text_response(StatusCode::BAD_REQUEST, "Task is not a BitTorrent download");
    }

    let target = match initial_task
        .files
        .iter()
        .find(|file| file.index == file_index.to_string())
    {
        Some(file) => file.clone(),
        None => return text_response(StatusCode::NOT_FOUND, "Torrent file was not found"),
    };
    let file_length = match target.length.parse::<u64>() {
        Ok(length) if length > 0 => length,
        _ => return text_response(StatusCode::NOT_FOUND, "Torrent file has no streamable data"),
    };

    let requested = match parse_range(
        headers
            .get(header::RANGE)
            .and_then(|value| value.to_str().ok()),
        file_length,
    ) {
        Ok(range) => range,
        Err(()) => return range_not_satisfiable(file_length),
    };
    let requested_end = requested.1.min(
        requested
            .0
            .saturating_add(STREAM_CHUNK_BYTES.saturating_sub(1)),
    );

    let available_end =
        match wait_for_available_end(&state.aria2, &gid, file_index, requested.0, requested_end)
            .await
        {
            Ok(Some(end)) => end,
            Ok(None) => {
                let mut response = text_response(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "Torrent pieces for this playback range are still buffering",
                );
                response
                    .headers_mut()
                    .insert(header::RETRY_AFTER, header::HeaderValue::from_static("1"));
                return response;
            }
            Err(error) => {
                return text_response(
                    StatusCode::BAD_GATEWAY,
                    &format!("Torrent streaming failed: {error}"),
                )
            }
        };

    let mut file = match File::open(&target.path).await {
        Ok(file) => file,
        Err(error) => {
            return text_response(
                StatusCode::SERVICE_UNAVAILABLE,
                &format!("Buffered torrent file is not ready yet: {error}"),
            )
        }
    };
    let on_disk_length = match file.metadata().await {
        Ok(metadata) => metadata.len(),
        Err(error) => {
            return text_response(
                StatusCode::SERVICE_UNAVAILABLE,
                &format!("Could not inspect buffered torrent file: {error}"),
            )
        }
    };
    if on_disk_length <= requested.0 {
        return text_response(
            StatusCode::SERVICE_UNAVAILABLE,
            "Torrent range is still buffering",
        );
    }

    let actual_end = available_end.min(on_disk_length.saturating_sub(1));
    if actual_end < requested.0 {
        return text_response(
            StatusCode::SERVICE_UNAVAILABLE,
            "Torrent range is still buffering",
        );
    }
    let byte_count = actual_end - requested.0 + 1;
    if file.seek(SeekFrom::Start(requested.0)).await.is_err() {
        return text_response(
            StatusCode::INTERNAL_SERVER_ERROR,
            "Could not seek torrent file",
        );
    }

    let mut buffer = vec![0_u8; byte_count as usize];
    if let Err(error) = file.read_exact(&mut buffer).await {
        return text_response(
            StatusCode::SERVICE_UNAVAILABLE,
            &format!("Torrent range became unavailable while reading: {error}"),
        );
    }

    let content_range = format!("bytes {}-{actual_end}/{file_length}", requested.0);
    let content_length = byte_count.to_string();
    let mime = media_content_type(&target.path);

    let builder = Response::builder()
        .status(StatusCode::PARTIAL_CONTENT)
        .header(header::ACCEPT_RANGES, "bytes")
        .header(header::CACHE_CONTROL, "no-store")
        .header(header::CONTENT_TYPE, mime)
        .header(header::CONTENT_RANGE, content_range)
        .header(header::CONTENT_LENGTH, content_length);
    match builder.body(Body::from(buffer)) {
        Ok(response) => response,
        Err(_) => text_response(
            StatusCode::INTERNAL_SERVER_ERROR,
            "Could not build stream response",
        ),
    }
}

async fn wait_for_available_end(
    aria2: &Aria2Client,
    gid: &str,
    file_index: u64,
    start: u64,
    end: u64,
) -> Result<Option<u64>, AppError> {
    let started = Instant::now();
    loop {
        let task = aria2.tell_status(gid).await?;
        if task.status == "error" || task.status == "removed" {
            return Err(AppError::Aria2(task.error_message.unwrap_or_else(|| {
                format!("Torrent entered {} state", task.status)
            })));
        }
        if task.status == "paused" {
            let _ = aria2.unpause(gid).await;
        }

        if let Some(available_end) = contiguous_available_end(&task, file_index, start, end) {
            return Ok(Some(available_end));
        }
        if started.elapsed() >= STREAM_WAIT_TIMEOUT {
            return Ok(None);
        }
        tokio::time::sleep(STREAM_POLL_INTERVAL).await;
    }
}

fn contiguous_available_end(
    task: &Aria2Task,
    file_index: u64,
    local_start: u64,
    local_end: u64,
) -> Option<u64> {
    let target = task
        .files
        .iter()
        .find(|file| file.index == file_index.to_string())?;
    let file_length = target.length.parse::<u64>().ok()?;
    if file_length == 0 || local_start >= file_length {
        return None;
    }
    let local_end = local_end.min(file_length - 1);
    if target.completed_length.parse::<u64>().ok()? >= file_length || task.status == "complete" {
        return Some(local_end);
    }

    let piece_length = task.piece_length.as_deref()?.parse::<u64>().ok()?;
    if piece_length == 0 {
        return None;
    }
    let bitfield = task.bitfield.as_deref()?;
    if bitfield.is_empty() {
        return None;
    }

    let file_offset = task
        .files
        .iter()
        .filter_map(|file| {
            let index = file.index.parse::<u64>().ok()?;
            let length = file.length.parse::<u64>().ok()?;
            Some((index, length))
        })
        .filter(|(index, _)| *index < file_index)
        .map(|(_, length)| length)
        .sum::<u64>();

    let global_start = file_offset.saturating_add(local_start);
    let global_end = file_offset.saturating_add(local_end);
    let first_piece = global_start / piece_length;
    let last_piece = global_end / piece_length;
    if !piece_is_complete(bitfield, first_piece) {
        return None;
    }

    let mut last_complete_piece = first_piece;
    for piece in first_piece.saturating_add(1)..=last_piece {
        if !piece_is_complete(bitfield, piece) {
            break;
        }
        last_complete_piece = piece;
    }

    let completed_global_end = last_complete_piece
        .saturating_add(1)
        .saturating_mul(piece_length)
        .saturating_sub(1)
        .min(global_end);
    completed_global_end.checked_sub(file_offset)
}

fn piece_is_complete(bitfield: &str, piece_index: u64) -> bool {
    let nibble_index = (piece_index / 4) as usize;
    let bit_in_nibble = (piece_index % 4) as u32;
    let Some(nibble) = bitfield
        .as_bytes()
        .get(nibble_index)
        .and_then(|value| char::from(*value).to_digit(16))
    else {
        return false;
    };
    let mask = 1_u32 << (3 - bit_in_nibble);
    nibble & mask != 0
}

fn parse_range(range: Option<&str>, file_length: u64) -> Result<(u64, u64), ()> {
    if file_length == 0 {
        return Err(());
    }
    let Some(range) = range else {
        return Ok((0, file_length - 1));
    };
    let spec = range.strip_prefix("bytes=").ok_or(())?;
    if spec.contains(',') {
        return Err(());
    }
    let (start_raw, end_raw) = spec.split_once('-').ok_or(())?;

    if start_raw.is_empty() {
        let suffix = end_raw.parse::<u64>().map_err(|_| ())?;
        if suffix == 0 {
            return Err(());
        }
        let length = suffix.min(file_length);
        return Ok((file_length - length, file_length - 1));
    }

    let start = start_raw.parse::<u64>().map_err(|_| ())?;
    if start >= file_length {
        return Err(());
    }
    let end = if end_raw.is_empty() {
        file_length - 1
    } else {
        end_raw.parse::<u64>().map_err(|_| ())?.min(file_length - 1)
    };
    if end < start {
        return Err(());
    }
    Ok((start, end))
}

fn media_content_type(path: &str) -> &'static str {
    let extension = path.rsplit('.').next().unwrap_or("").to_ascii_lowercase();
    match extension.as_str() {
        "mp4" | "m4v" => "video/mp4",
        "webm" => "video/webm",
        "mkv" => "video/x-matroska",
        "mov" => "video/quicktime",
        "avi" => "video/x-msvideo",
        "mp3" => "audio/mpeg",
        "m4a" | "aac" => "audio/mp4",
        "ogg" | "oga" => "audio/ogg",
        "opus" => "audio/ogg",
        "flac" => "audio/flac",
        "wav" => "audio/wav",
        _ => "application/octet-stream",
    }
}

fn range_not_satisfiable(file_length: u64) -> Response<Body> {
    let builder = Response::builder()
        .status(StatusCode::RANGE_NOT_SATISFIABLE)
        .header(header::CONTENT_RANGE, format!("bytes */{file_length}"));
    match builder.body(Body::from("Requested range is not satisfiable")) {
        Ok(response) => response,
        Err(_) => Response::new(Body::empty()),
    }
}

fn text_response(status: StatusCode, message: &str) -> Response<Body> {
    let builder = Response::builder()
        .status(status)
        .header(header::CONTENT_TYPE, "text/plain; charset=utf-8")
        .header(header::CACHE_CONTROL, "no-store");
    match builder.body(Body::from(message.to_string())) {
        Ok(response) => response,
        Err(_) => Response::new(Body::empty()),
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_range, piece_is_complete};

    #[test]
    fn parses_open_ended_range() {
        assert_eq!(parse_range(Some("bytes=100-"), 1000), Ok((100, 999)));
    }

    #[test]
    fn parses_suffix_range() {
        assert_eq!(parse_range(Some("bytes=-100"), 1000), Ok((900, 999)));
    }

    #[test]
    fn rejects_out_of_bounds_range() {
        assert!(parse_range(Some("bytes=1000-"), 1000).is_err());
    }

    #[test]
    fn bitfield_uses_high_bit_for_piece_zero() {
        assert!(piece_is_complete("80", 0));
        assert!(!piece_is_complete("80", 1));
        assert!(piece_is_complete("40", 1));
    }
}
