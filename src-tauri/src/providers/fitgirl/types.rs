use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FitGirlPage {
    pub title: String,
    pub description: String,
    pub features: Vec<String>,
    pub dlcs: Vec<String>,
    pub magnet_links: Vec<String>,
    pub fuckingfast_links: Vec<String>,
    pub images: Vec<String>,
    pub repack_size: Option<String>,
}
