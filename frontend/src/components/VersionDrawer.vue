<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useScoopStore } from '../stores/scoop'
import * as api from '../api'
import type { AppInfo, VersionInfo, RelatedApp } from '../types'

const props = defineProps<{
  visible: boolean
  app: AppInfo | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const store = useScoopStore()
const versions = ref<VersionInfo[]>([])
const relatedApps = ref<RelatedApp[]>([])
const loadingVersions = ref(false)
const loadingRelated = ref(false)
const operating = ref(false)
const targetVersion = ref('')
const selectedRelatedApp = ref<RelatedApp | null>(null)
const activeTab = ref<'version' | 'related'>('version')

watch(() => props.visible, async (val) => {
  if (val && props.app) {
    activeTab.value = 'version'
    targetVersion.value = ''
    selectedRelatedApp.value = null

    loadingVersions.value = true
    loadingRelated.value = true

    try {
      versions.value = await api.getVersions(props.app.name)
    } catch {
      versions.value = []
    } finally {
      loadingVersions.value = false
    }

    try {
      relatedApps.value = await api.getRelatedApps(props.app.name)
    } catch {
      relatedApps.value = []
    } finally {
      loadingRelated.value = false
    }
  }
})

function close() {
  emit('update:visible', false)
  targetVersion.value = ''
  selectedRelatedApp.value = null
}

async function handleReset() {
  if (!props.app || !targetVersion.value) return

  try {
    await ElMessageBox.confirm(
      `确定要将 ${props.app.name} 切换到版本 ${targetVersion.value} 吗？`,
      '确认切换版本',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  operating.value = true
  try {
    await store.resetApp(props.app.name, targetVersion.value)
    ElMessage.success(`已切换 ${props.app.name} 到版本 ${targetVersion.value}`)
    close()
  } catch (e: unknown) {
    ElMessage.error('切换失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    operating.value = false
  }
}

async function handleSwitchRelated() {
  if (!props.app || !selectedRelatedApp.value) return

  try {
    await ElMessageBox.confirm(
      `确定要切换到 ${selectedRelatedApp.value.name} 吗？\n共享的可执行文件：${selectedRelatedApp.value.shared_bins.join(', ')}`,
      '确认切换应用',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  operating.value = true
  try {
    await store.resetApp(props.app.name, undefined, selectedRelatedApp.value.name)
    ElMessage.success(`已切换到 ${selectedRelatedApp.value.name}`)
    close()
  } catch (e: unknown) {
    ElMessage.error('切换失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    operating.value = false
  }
}

function selectRelatedApp(app: RelatedApp) {
  selectedRelatedApp.value = selectedRelatedApp.value?.name === app.name ? null : app
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    title="版本管理"
    direction="rtl"
    size="480px"
    @close="close"
  >
    <template v-if="app">
      <div class="app-info">
        <h3>{{ app.name }}</h3>
        <p>当前版本：<el-tag>{{ app.version }}</el-tag></p>
        <p>Bucket：{{ app.bucket }}</p>
      </div>

      <el-divider />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="版本切换" name="version">
          <div class="version-section">
            <h4>目标版本</h4>
            <el-input
              v-model="targetVersion"
              placeholder="输入版本号，如 24.08"
              clearable
              style="margin-bottom: 12px"
            />

            <div v-if="loadingVersions" class="loading-hint">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在搜索...
            </div>

            <div v-else-if="versions.length > 0" class="version-list">
              <p class="hint">在各 bucket 中找到的版本（点击选择）：</p>
              <el-tag
                v-for="v in versions"
                :key="`${v.name}-${v.bucket}`"
                :type="v.version === targetVersion ? 'primary' : 'info'"
                class="version-tag"
                @click="targetVersion = v.version"
              >
                {{ v.version }} [{{ v.bucket }}]
              </el-tag>
            </div>

            <div v-else class="no-versions">
              <p class="hint">未在其他 bucket 中找到此软件的其他版本。</p>
              <p class="hint">你可以手动输入版本号尝试切换。</p>
            </div>
          </div>

          <el-divider />

          <div class="actions">
            <el-button
              type="primary"
              :disabled="!targetVersion"
              :loading="operating"
              @click="handleReset"
            >
              切换版本
            </el-button>
          </div>

          <div class="tips">
            <el-alert type="info" :closable="false">
              <template #title>
                <strong>切换版本</strong>：使用 scoop reset app@version，需要先安装多个版本才能切换。
              </template>
            </el-alert>
          </div>
        </el-tab-pane>

        <el-tab-pane label="关联应用切换" name="related">
          <div class="related-section">
            <div v-if="loadingRelated" class="loading-hint">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在查找关联应用...
            </div>

            <div v-else-if="relatedApps.length > 0" class="related-list">
              <p class="hint">以下已安装的应用与当前应用共享可执行文件，可以直接切换：</p>
              <div
                v-for="ra in relatedApps"
                :key="ra.name"
                class="related-item"
                :class="{ selected: selectedRelatedApp?.name === ra.name }"
                @click="selectRelatedApp(ra)"
              >
                <div class="related-info">
                  <span class="related-name">{{ ra.name }}</span>
                  <el-tag size="small" type="info">{{ ra.version }}</el-tag>
                  <span class="related-bucket">[{{ ra.bucket }}]</span>
                </div>
                <div class="shared-bins">
                  共享：{{ ra.shared_bins.join(', ') }}
                </div>
              </div>
            </div>

            <div v-else class="no-related">
              <el-empty description="未找到关联应用" :image-size="80" />
              <p class="hint">没有已安装的应用与当前应用共享可执行文件。</p>
              <p class="hint">例如：安装 openjdk8 和 openjdk17 后，它们会共享 java.exe，可以互相切换。</p>
            </div>
          </div>

          <el-divider v-if="relatedApps.length > 0" />

          <div v-if="relatedApps.length > 0" class="actions">
            <el-button
              type="primary"
              :disabled="!selectedRelatedApp"
              :loading="operating"
              @click="handleSwitchRelated"
            >
              切换到选中应用
            </el-button>
          </div>

          <div class="tips" style="margin-top: 16px">
            <el-alert type="info" :closable="false">
              <template #title>
                <strong>关联应用切换</strong>：使用 scoop reset 切换到共享相同可执行文件的其他应用。
              </template>
            </el-alert>
            <el-alert type="success" :closable="false" style="margin-top: 8px">
              <template #title>
                <strong>典型场景</strong>：在 openjdk8、openjdk11、openjdk17 等不同 JDK 版本间切换。
              </template>
            </el-alert>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </el-drawer>
</template>

<script lang="ts">
import { Loading } from '@element-plus/icons-vue'
export default {
  components: { Loading }
}
</script>

<style scoped>
.app-info h3 {
  margin-bottom: 12px;
  color: #303133;
}

.app-info p {
  margin: 8px 0;
  color: #606266;
}

.version-section h4 {
  margin-bottom: 12px;
  color: #303133;
}

.loading-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.version-list .hint,
.no-versions .hint,
.related-section .hint,
.no-related .hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.version-tag {
  margin: 4px;
  cursor: pointer;
}

.actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.tips {
  margin-top: 20px;
}

.related-section {
  min-height: 150px;
}

.related-list {
  margin-top: 8px;
}

.related-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.related-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.related-item.selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.related-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.related-name {
  font-weight: 500;
  color: #303133;
}

.related-bucket {
  font-size: 12px;
  color: #909399;
}

.shared-bins {
  font-size: 12px;
  color: #67c23a;
}

.no-related {
  text-align: center;
  padding: 20px 0;
}
</style>
