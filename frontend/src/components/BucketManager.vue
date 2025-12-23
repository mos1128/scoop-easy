<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useScoopStore } from '../stores/scoop'
import * as api from '../api'
import type { BucketInfo } from '../types'

const store = useScoopStore()
const buckets = ref<BucketInfo[]>([])
const selectedBuckets = ref<BucketInfo[]>([])
const loading = ref(false)
const addDialogVisible = ref(false)
const adding = ref(false)
const newBucket = ref({ name: '', url: '' })

async function loadBuckets() {
  loading.value = true
  try {
    buckets.value = await api.getBuckets()
  } finally {
    loading.value = false
  }
}

async function autoRefresh() {
  if (!store.turboMode) {
    await loadBuckets()
  }
}

function openAddDialog() {
  newBucket.value = { name: '', url: '' }
  addDialogVisible.value = true
}

async function handleAdd() {
  if (!newBucket.value.name) {
    ElMessage.warning('请输入Bucket名称')
    return
  }
  adding.value = true
  try {
    await api.addBucket(newBucket.value.name, newBucket.value.url || undefined)
    ElMessage.success(`已添加 ${newBucket.value.name}`)
    addDialogVisible.value = false
    await autoRefresh()
  } catch (e: unknown) {
    ElMessage.error('添加失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    adding.value = false
  }
}

async function handleRemove(bucket: BucketInfo) {
  try {
    await ElMessageBox.confirm(
      `确定要移除 ${bucket.name} 吗？`,
      '确认移除',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.removeBucket(bucket.name)
    ElMessage.success(`已移除 ${bucket.name}`)
    await autoRefresh()
  } catch (e: unknown) {
    ElMessage.error('移除失败：' + (e instanceof Error ? e.message : String(e)))
  }
}

function openUrl(url: string) {
  window.open(url, '_blank')
}

function handleSelectionChange(selection: BucketInfo[]) {
  selectedBuckets.value = selection
}

async function handleBatchRemove() {
  if (selectedBuckets.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要移除选中的 ${selectedBuckets.value.length} 个Bucket吗？`,
      '确认移除',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  for (const bucket of selectedBuckets.value) {
    try {
      await api.removeBucket(bucket.name)
    } catch {
      // continue
    }
  }
  ElMessage.success('移除完成')
  selectedBuckets.value = []
  await autoRefresh()
}

onMounted(() => {
  loadBuckets()
})
</script>

<template>
  <div class="bucket-manager">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" :icon="Plus" @click="openAddDialog">添加 Bucket</el-button>
        <el-button
          type="danger"
          :icon="Delete"
          :disabled="selectedBuckets.length === 0"
          @click="handleBatchRemove"
        >
          移除选中 ({{ selectedBuckets.length }})
        </el-button>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadBuckets">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="buckets"
      style="width: 100%"
      height="calc(100vh - 200px)"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="name" label="名称" width="150" sortable>
        <template #default="{ row }">
          <span class="bucket-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="地址" min-width="300">
        <template #default="{ row }">
          <el-link type="primary" @click="openUrl(row.source)">
            {{ row.source }}
            <el-icon class="link-icon"><Link /></el-icon>
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="updated" label="更新时间" width="180" />
      <el-table-column label="软件数" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.manifests" type="info" size="small">{{ row.manifests }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-tooltip content="移除">
              <el-button type="danger" :icon="Delete" size="small" @click="handleRemove(row)" />
            </el-tooltip>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="addDialogVisible" title="添加 Bucket" width="500px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="newBucket.name" placeholder="如：extras, versions, java" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="newBucket.url" placeholder="可选，留空使用官方源" />
          <div class="form-tip">官方Bucket无需填写地址，自定义Bucket需填写Git仓库地址</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="handleAdd">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { Plus, Refresh, Delete, Link } from '@element-plus/icons-vue'
export default {
  components: { Plus, Refresh, Delete, Link }
}
</script>

<style scoped>
.bucket-manager {
  height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.bucket-name {
  font-weight: 500;
}

.link-icon {
  margin-left: 4px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
