import axios from 'axios'
import type { AppInfo, VersionInfo, BucketInfo, SearchResult, AppManifest, Settings, RelatedApp, OperationLog } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export async function getApps(): Promise<AppInfo[]> {
  const { data } = await api.get<AppInfo[]>('/apps')
  return data
}

export async function updateApps(apps: string[]): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post('/apps/update', { apps })
  return data
}

export async function uninstallApps(apps: string[]): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post('/apps/uninstall', { apps })
  return data
}

export async function holdApp(name: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post(`/apps/${name}/hold`)
  return data
}

export async function unholdApp(name: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete(`/apps/${name}/hold`)
  return data
}

export async function holdApps(apps: string[]): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post('/apps/hold', { apps })
  return data
}

export async function unholdApps(apps: string[]): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete('/apps/hold', { data: { apps } })
  return data
}

export async function getVersions(name: string): Promise<VersionInfo[]> {
  const { data } = await api.get<VersionInfo[]>(`/apps/${name}/versions`)
  return data
}

export async function getRelatedApps(name: string): Promise<RelatedApp[]> {
  const { data } = await api.get<RelatedApp[]>(`/apps/${name}/related`)
  return data
}

export async function resetApp(name: string, version?: string, targetApp?: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post(`/apps/${name}/reset`, { version, target_app: targetApp })
  return data
}

export async function getBuckets(): Promise<BucketInfo[]> {
  const { data } = await api.get<BucketInfo[]>('/buckets')
  return data
}

export async function addBucket(name: string, url?: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post('/buckets', { name, url })
  return data
}

export async function removeBucket(name: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete(`/buckets/${name}`)
  return data
}

export async function getSettings(): Promise<Settings> {
  const { data } = await api.get<Settings>('/settings')
  return data
}

export async function updateSettings(settings: Partial<Settings>): Promise<{ success: boolean }> {
  const { data } = await api.post('/settings', settings)
  return data
}

export async function searchApps(query: string): Promise<SearchResult[]> {
  const { data } = await api.get<SearchResult[]>('/search', { params: { q: query } })
  return data
}

export async function installApp(bucket: string, name: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post(`/apps/install`, { bucket }, { params: { name } })
  return data
}

export async function getAppInfo(name: string): Promise<AppManifest> {
  const { data } = await api.get<AppManifest>(`/apps/${name}/info`)
  return data
}

export async function getLogs(limit: number = 100): Promise<OperationLog[]> {
  const { data } = await api.get<OperationLog[]>('/logs', { params: { limit } })
  return data
}

export async function clearLogs(): Promise<{ success: boolean }> {
  const { data } = await api.delete('/logs')
  return data
}
