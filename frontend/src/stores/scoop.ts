import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppInfo, Settings } from '../types'
import * as api from '../api'

export const useScoopStore = defineStore('scoop', () => {
  const apps = ref<AppInfo[]>([])
  const loading = ref(false)
  const searchQuery = ref('')
  const filterStatus = ref<'all' | 'updates' | 'held'>('all')
  const settings = ref<Settings>({ search_command: 'scoop', turbo_mode: false })

  const filteredApps = computed(() => {
    let result = apps.value

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(app => app.name.toLowerCase().includes(query))
    }

    if (filterStatus.value === 'updates') {
      result = result.filter(app => app.has_update)
    } else if (filterStatus.value === 'held') {
      result = result.filter(app => app.held)
    }

    return result
  })

  const updateCount = computed(() => apps.value.filter(app => app.has_update).length)
  const heldCount = computed(() => apps.value.filter(app => app.held).length)
  const turboMode = computed(() => settings.value.turbo_mode ?? false)

  async function loadSettings() {
    try {
      settings.value = await api.getSettings()
    } catch {
      // use default
    }
  }

  async function saveSettings(newSettings: Partial<Settings>) {
    const merged = { ...settings.value, ...newSettings }
    await api.updateSettings(merged)
    settings.value = merged
  }

  async function loadApps() {
    loading.value = true
    try {
      apps.value = await api.getApps()
    } finally {
      loading.value = false
    }
  }

  async function autoRefresh() {
    if (!turboMode.value) {
      await loadApps()
    }
  }

  async function updateApps(names: string[]) {
    await api.updateApps(names)
    await autoRefresh()
  }

  async function uninstallApps(names: string[]) {
    await api.uninstallApps(names)
    await autoRefresh()
  }

  async function toggleHold(name: string, held: boolean) {
    if (held) {
      await api.unholdApp(name)
    } else {
      await api.holdApp(name)
    }
    await autoRefresh()
  }

  async function unholdApps(names: string[]) {
    await api.unholdApps(names)
    await autoRefresh()
  }

  async function resetApp(name: string, version?: string, targetApp?: string) {
    const result = await api.resetApp(name, version, targetApp)
    await autoRefresh()
    return result
  }

  return {
    apps,
    loading,
    searchQuery,
    filterStatus,
    filteredApps,
    updateCount,
    heldCount,
    settings,
    turboMode,
    loadSettings,
    saveSettings,
    loadApps,
    updateApps,
    uninstallApps,
    toggleHold,
    unholdApps,
    resetApp,
  }
})
