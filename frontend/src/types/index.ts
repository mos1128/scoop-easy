export interface AppInfo {
  name: string
  version: string
  bucket: string
  updated?: string
  held: boolean
  has_update: boolean
  latest_version?: string
}

export interface VersionInfo {
  name: string
  version: string
  bucket: string
}

export interface RelatedApp {
  name: string
  version: string
  bucket: string
  shared_bins: string[]
}

export interface BucketInfo {
  name: string
  source: string
  updated?: string
  manifests?: number
}

export interface SearchResult {
  name: string
  version: string
  bucket: string
  description?: string
}

export interface AppManifest {
  name: string
  version: string
  description?: string
  homepage?: string
  license?: string
  bin?: string[]
  shortcuts?: string[]
}

export interface Settings {
  search_command: 'scoop' | 'scoop-search'
  turbo_mode?: boolean
}

export interface OperationLog {
  time: string
  operation: string
  command: string
  success: boolean
  message: string
}
