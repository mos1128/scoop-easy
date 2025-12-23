<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '../api'
import type { SearchResult } from '../types'

const searchQuery = ref('')
const results = ref<SearchResult[]>([])
const loading = ref(false)
const installing = ref<string | null>(null)

async function handleSearch() {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  results.value = []
  try {
    results.value = await api.searchApps(searchQuery.value.trim())
    if (results.value.length === 0) {
      ElMessage.info('未找到匹配的软件')
    }
  } catch (e: unknown) {
    ElMessage.error('搜索失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    loading.value = false
  }
}

async function handleInstall(app: SearchResult) {
  installing.value = app.name
  try {
    await api.installApp(app.name, app.version)
    ElMessage.success(`已安装 ${app.name}`)
  } catch (e: unknown) {
    ElMessage.error('安装失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    installing.value = null
  }
}
</script>

<template>
  <div class="search-page">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="输入软件名称搜索..."
          :prefix-icon="Search"
          clearable
          style="width: 400px"
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" :icon="Search" :loading="loading" @click="handleSearch">
          搜索
        </el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="results"
      style="width: 100%"
      height="calc(100vh - 200px)"
    >
      <el-table-column prop="name" label="软件名称" min-width="200" sortable>
        <template #default="{ row }">
          <span class="app-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="150">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.version }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="bucket" label="Bucket" width="120" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            :icon="Download"
            size="small"
            :loading="installing === row.name"
            @click="handleInstall(row)"
          >
            安装
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && results.length === 0 && searchQuery" description="暂无搜索结果" />
  </div>
</template>

<script lang="ts">
import { Search, Download } from '@element-plus/icons-vue'
export default {
  components: { Search, Download }
}
</script>

<style scoped>
.search-page {
  height: 100%;
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.app-name {
  font-weight: 500;
}
</style>
