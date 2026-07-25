export interface SearchResult {
  title: string;
  url: string;
  image?: string;
  description?: string;
  category?: string;
  size?: string;
}

export interface GameDetail {
  title: string;
  images: string[];
  description: string;
  features: string[];
  dlcs: string[];
  magnet_links: string[];
  repack_size?: string;
}

export interface ProviderStatus {
  name: string;
  enabled: boolean;
  error?: string;
}
