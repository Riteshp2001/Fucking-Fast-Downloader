use crate::providers::error::ProviderError;
use crate::providers::fitgirl::types::FitGirlPage;
use crate::providers::SearchResult;
use scraper::{ElementRef, Html, Selector};

/// Parses a FitGirl game article HTML page.
pub fn parse_game_article(html: &str) -> Result<FitGirlPage, ProviderError> {
    let document = Html::parse_document(html);

    // Title
    let title_sel = Selector::parse("h1.entry-title")
        .map_err(|_| ProviderError::Parse("Invalid title selector".into()))?;
    let title = document
        .select(&title_sel)
        .next()
        .and_then(|el| el.text().collect::<String>().into())
        .map(|s: String| s.trim().to_string())
        .unwrap_or_default();

    // Entry content
    let content_sel = Selector::parse(".entry-content")
        .map_err(|_| ProviderError::Parse("Invalid content selector".into()))?;
    let entry_content = document
        .select(&content_sel)
        .next()
        .ok_or_else(|| ProviderError::Parse("No .entry-content found".into()))?;

    let inner_html = entry_content.inner_html();

    // Description: first paragraphs
    let description = extract_description(&document, &content_sel);

    // Features from "Game Features" list
    let features = extract_section_list(&inner_html, "Game Features");

    // DLCs from "Included DLCs" list
    let dlcs = extract_section_list(&inner_html, "Included DLC");

    // Magnet links
    let magnet_links = extract_magnet_links(&document);
    let fuckingfast_links = extract_fuckingfast_links(&document);

    // Images from paragraphs 3-6
    let images = extract_images(&entry_content);

    // Repack size
    let repack_size = extract_repack_size(&inner_html);

    Ok(FitGirlPage {
        title,
        description,
        features,
        dlcs,
        magnet_links,
        fuckingfast_links,
        images,
        repack_size,
    })
}

/// Extracts list items under a section heading (e.g., "Game Features", "Included DLCs").
fn extract_section_list(html: &str, section_title: &str) -> Vec<String> {
    let doc = Html::parse_fragment(html);

    // Find heading containing the section title
    let heading_sel = Selector::parse("strong, h3, h4").expect("Invalid heading selector");

    for heading in doc.select(&heading_sel) {
        let text: String = heading.text().collect();
        if text.contains(section_title) {
            // Walk siblings from the heading's parent to find the next ul element
            let mut current = heading.parent().and_then(|p| p.next_sibling());
            while let Some(sibling) = current {
                if sibling.value().is_element() {
                    let is_ul = sibling
                        .value()
                        .as_element()
                        .map_or(false, |e| e.name() == "ul");
                    if is_ul {
                        if let Some(ul_ref) = ElementRef::wrap(sibling) {
                            return ul_ref
                                .text()
                                .filter_map(|t| {
                                    let s = t.trim().to_string();
                                    if s.is_empty() {
                                        None
                                    } else {
                                        Some(s)
                                    }
                                })
                                .collect();
                        }
                    }
                }
                current = sibling.next_sibling();
            }
            break;
        }
    }

    Vec::new()
}

/// Extracts magnet links from the document.
fn extract_magnet_links(document: &Html) -> Vec<String> {
    let magnet_sel = Selector::parse("a[href^=\"magnet:?\"]").expect("Invalid magnet selector");
    document
        .select(&magnet_sel)
        .filter_map(|a| a.attr("href").map(|h| h.to_string()))
        .collect()
}

/// Extracts unique FuckingFast share links from the document.
fn extract_fuckingfast_links(document: &Html) -> Vec<String> {
    let link_sel = Selector::parse("a[href]").expect("Invalid link selector");
    let mut links = Vec::new();

    for href in document.select(&link_sel).filter_map(|a| a.attr("href")) {
        let lower = href.to_ascii_lowercase();
        if !lower.contains("fuckingfast.co") || lower.contains("dl.fuckingfast.co") {
            continue;
        }

        let href = href.trim().to_string();
        if !links.iter().any(|existing| existing == &href) {
            links.push(href);
        }
    }

    links
}

/// Extracts images from the entry content paragraphs.
fn extract_images(entry_content: &scraper::ElementRef) -> Vec<String> {
    let img_sel = Selector::parse("img").expect("Invalid img selector");
    entry_content
        .select(&img_sel)
        .filter_map(|img| {
            let src = img.attr("src")?;
            // Convert 240p JPG to 1080p WebP via wsrv.nl
            Some(upscale_image_url(src))
        })
        .take(5)
        .collect()
}

/// Converts a 240p FitGirl image URL to 1080p WebP via wsrv.nl.
fn upscale_image_url(url: &str) -> String {
    if url.contains("wp-content") {
        // Proxy through wsrv.nl for WebP conversion + upscaling
        format!(
            "https://wsrv.nl/?url={}&output=webp&w=1920",
            urlencoding(url)
        )
    } else {
        url.to_string()
    }
}

fn urlencoding(url: &str) -> String {
    urlencoding::encode(url).into_owned()
}

/// Extracts description from the first paragraphs of entry content.
fn extract_description(document: &Html, _content_sel: &Selector) -> String {
    let p_sel = Selector::parse("p").expect("Invalid p selector");
    document
        .select(&p_sel)
        .take(3)
        .map(|p| p.text().collect::<String>())
        .collect::<Vec<_>>()
        .join("\n")
        .trim()
        .to_string()
}

/// Extracts repack size from text patterns like "Size: 5.6 GB" or "Repack Size: 5.6 GB".
fn extract_repack_size(html: &str) -> Option<String> {
    let re = regex::Regex::new(r"(?i)(?:size|repack\s*size)[:\s]+([\d.]+\s*(?:GB|MB|TB))").ok()?;
    re.captures(html)
        .and_then(|c| c.get(1).map(|m| m.as_str().to_string()))
}

/// Parses search results HTML from FitGirl search page.
pub fn parse_article_search_result(html: &str, url: &str) -> Result<SearchResult, ProviderError> {
    let page = parse_game_article(html)?;
    let image = page.images.first().cloned();

    Ok(SearchResult {
        title: page.title,
        url: url.to_string(),
        image,
        description: if page.description.is_empty() {
            None
        } else {
            Some(page.description)
        },
        category: None,
        size: page.repack_size,
    })
}

/// Parses search results HTML from FitGirl search page.
pub fn parse_search_results(html: &str) -> Result<Vec<SearchResult>, ProviderError> {
    let document = Html::parse_document(html);
    let article_sel = Selector::parse("article")
        .map_err(|_| ProviderError::Parse("Invalid search selector".into()))?;

    let link_sel = Selector::parse("a").expect("Invalid a selector");
    let title_sel = Selector::parse(".entry-title a, h1 a, h2 a, a[rel=\"bookmark\"]")
        .expect("Invalid title selector");
    let img_sel = Selector::parse("img").expect("Invalid img selector");

    let mut results: Vec<SearchResult> = document
        .select(&article_sel)
        .filter_map(|article| {
            let link = article
                .select(&title_sel)
                .next()
                .or_else(|| article.select(&link_sel).next())?;
            let title: String = link.text().collect();
            let href = link.attr("href")?.to_string();
            let title = title.trim().to_string();
            if title.is_empty() || href.is_empty() {
                return None;
            }

            // Try to find a post thumbnail
            let img = article
                .select(&img_sel)
                .next()
                .and_then(|img| img.attr("src"))
                .map(|s| upscale_image_url(s));

            Some(SearchResult {
                title,
                url: href,
                image: img,
                description: None,
                category: None,
                size: None,
            })
        })
        .collect();

    if results.is_empty() {
        let entry_title_sel =
            Selector::parse(".entry-title a").expect("Invalid entry-title selector");
        results = document
            .select(&entry_title_sel)
            .filter_map(|link| {
                let title = link.text().collect::<String>().trim().to_string();
                let href = link.attr("href")?.to_string();
                if title.is_empty() || href.is_empty() {
                    return None;
                }
                Some(SearchResult {
                    title,
                    url: href,
                    image: None,
                    description: None,
                    category: None,
                    size: None,
                })
            })
            .collect();
    }

    if results.is_empty() {
        return Err(ProviderError::NotFound("No search results found".into()));
    }

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    const SEARCH_FIXTURE: &str = include_str!("test_fixtures/search_results.html");
    const ARTICLE_FIXTURE: &str = include_str!("test_fixtures/game_article.html");

    #[test]
    fn test_parse_search_results_extracts_titles_and_links() {
        let results = parse_search_results(SEARCH_FIXTURE).expect("should parse");
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].title, "Test Game — Full Repack");
        assert!(results[0].url.contains("test-game"));
    }

    #[test]
    fn test_parse_search_results_extracts_images() {
        let results = parse_search_results(SEARCH_FIXTURE).expect("should parse");
        assert!(results[0].image.is_some());
        assert!(results[0].image.as_ref().unwrap().contains("wsrv.nl"));
    }

    #[test]
    fn test_parse_article_search_result_extracts_summary() {
        let result =
            parse_article_search_result(ARTICLE_FIXTURE, "https://fitgirl-repacks.site/test-game/")
                .expect("should parse");
        assert_eq!(result.title, "Test Game — Full Repack");
        assert_eq!(result.url, "https://fitgirl-repacks.site/test-game/");
        assert_eq!(result.size, Some("5.6 GB".into()));
        assert!(result.image.as_ref().unwrap().contains("wsrv.nl"));
    }

    #[test]
    fn test_parse_game_article_extracts_title() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert_eq!(page.title, "Test Game — Full Repack");
    }

    #[test]
    fn test_parse_game_article_extracts_features() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert!(page.features.iter().any(|f| f.contains("Feature one")));
    }

    #[test]
    fn test_parse_game_article_extracts_dlcs() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert!(page.dlcs.iter().any(|d| d.contains("DLC one")));
    }

    #[test]
    fn test_parse_game_article_extracts_magnet_links() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert!(page.magnet_links.iter().any(|m| m.starts_with("magnet:")));
    }

    #[test]
    fn test_parse_game_article_extracts_unique_fuckingfast_links() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert_eq!(
            page.fuckingfast_links,
            vec![
                "https://fuckingfast.co/test-part-1".to_string(),
                "https://fuckingfast.co/test-part-2?download=1".to_string(),
            ]
        );
    }

    #[test]
    fn test_parse_game_article_extracts_images() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert!(!page.images.is_empty());
        assert!(page.images[0].contains("wsrv.nl"));
    }

    #[test]
    fn test_parse_game_article_extracts_repack_size() {
        let page = parse_game_article(ARTICLE_FIXTURE).expect("should parse");
        assert_eq!(page.repack_size, Some("5.6 GB".into()));
    }

    #[test]
    fn test_upscale_image_url_transforms_wp_content() {
        let result = upscale_image_url(
            "https://fitgirl-repacks.site/wp-content/uploads/2024/01/game-240x180.jpg",
        );
        assert!(result.contains("wsrv.nl"));
        assert!(result.contains("output=webp"));
    }

    #[test]
    fn test_upscale_image_url_passthrough_non_wp() {
        let result = upscale_image_url("https://example.com/image.jpg");
        assert_eq!(result, "https://example.com/image.jpg");
    }
}
