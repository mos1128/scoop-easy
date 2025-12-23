<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '../api'
import type { OperationLog } from '../types'

const logs = ref<OperationLog[]>([])
const loading = ref(false)

async function loadLogs() {
  loading.value = true
  try {
    logs.value = await api.getLogs(200)
  } catch {
    logs.value = []
  } finally {
    loading.value = false
  }
}

async function handleClear() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有操作记录吗？此操作不可恢复。',
      '确认清空',
      { confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await api.clearLogs()
    logs.value = []
    ElMessage.success('操作记录已清空')
  } catch (e: unknown) {
    ElMessage.error('清空失败：' + (e instanceof Error ? e.message : String(e)))
  }
}

function formatTime(isoTime: string): string {
  const date = new Date(isoTime)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

onMounted(() => {
  loadLogs()
})
</script>

<template>
  <div class="operation-log">
    <div class="toolbar">
      <h3>操作记录</h3>
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadLogs" :loading="loading">刷新</el-button>
        <el-button type="danger" :icon="Delete" @click="handleClear" :disabled="logs.length === 0">清空</el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="logs"
      style="width: 100%"
      height="calc(100vh - 200px)"
    >
      <el-table-column label="时间" width="140">
        <template #default="{ row }">
          <span class="log-time">{{ formatTime(row.time) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-tag :type="row.success ? 'success' : 'danger'" size="small">
            {{ row.operation }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="命令" min-width="280">
        <template #default="{ row }">
          <code class="log-command">{{ row.command }}</code>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-icon v-if="row.success" color="#67C23A"><SuccessFilled /></el-icon>
          <el-icon v-else color="#F56C6C"><CircleCloseFilled /></el-icon>
        </template>
      </el-table-column>
      <el-table-column label="详情" width="80">
        <template #default="{ row }">
          <el-popover
            v-if="row.message"
            placement="left"
            :width="400"
            trigger="click"
          >
            <template #reference>
              <el-button :icon="View" size="small" text />
            </template>
            <pre class="log-message">{{ row.message }}</pre>
          </el-popover>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && logs.length === 0" description="暂无操作记录" />
  </div>
</template>

<script lang="ts">
import { Refresh, Delete, View, SuccessFilled, CircleCloseFilled } from '@element-plus/icons-vue'
export default {
  components: { Refresh, Delete, View, SuccessFilled, CircleCloseFilled }
}
</script>

<style scoped>
.operation-log {
  height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar h3 {
  margin: 0;
  color: #303133;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

.log-time {
  font-size: 12px;
  color: #909399;
  font-family: 'Consolas', 'Monaco', monospace;
}

.log-command {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
  word-break: break-all;
}

.log-message {
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow: auto;
}
</style>
