use reqwest::ClientBuilder;

pub(crate) fn apply_explicit_proxy(
    builder: ClientBuilder,
    proxy: &Option<String>,
    scope: &str,
) -> ClientBuilder {
    match proxy
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
    {
        Some(server) => match reqwest::Proxy::all(server) {
            Ok(proxy) => builder.proxy(proxy),
            Err(e) => {
                log::warn!("{scope}: invalid proxy config: {e}");
                builder.no_proxy()
            }
        },
        None => builder.no_proxy(),
    }
}
