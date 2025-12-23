<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useScoopStore } from './stores/scoop'
import VersionDrawer from './components/VersionDrawer.vue'
import BucketManager from './components/BucketManager.vue'
import SearchPage from './components/SearchPage.vue'
import AppInfoDialog from './components/AppInfoDialog.vue'
import OperationLog from './components/OperationLog.vue'
import type { AppInfo } from './types'

const store = useScoopStore()
const selectedApps = ref<AppInfo[]>([])
const versionDrawerVisible = ref(false)
const currentApp = ref<AppInfo | null>(null)
const operating = ref(false)
const currentView = ref<'apps' | 'buckets' | 'search' | 'logs'>('apps')
const appInfoVisible = ref(false)
const appInfoName = ref<string | null>(null)
const settingsVisible = ref(false)

onMounted(() => {
  store.loadSettings()
  store.loadApps()
})

function handleSelectionChange(selection: AppInfo[]) {
  selectedApps.value = selection
}

function showAppInfo(app: AppInfo) {
  appInfoName.value = app.name
  appInfoVisible.value = true
}

async function handleBatchUpdate() {
  const appsToUpdate = selectedApps.value.filter(app => app.has_update && !app.held)
  if (appsToUpdate.length === 0) {
    ElMessage.warning('所选软件没有可用更新或已被锁定')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要更新以下 ${appsToUpdate.length} 个软件吗？\n${appsToUpdate.map(a => a.name).join(', ')}`,
      '确认更新',
      { confirmButtonText: '更新', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }

  operating.value = true
  try {
    await store.updateApps(appsToUpdate.map(a => a.name))
    ElMessage.success(`成功更新 ${appsToUpdate.length} 个软件`)
  } catch (e: unknown) {
    ElMessage.error('更新失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    operating.value = false
    selectedApps.value = []
  }
}

async function handleBatchUninstall() {
  if (selectedApps.value.length === 0) {
    ElMessage.warning('请先选择要卸载的软件')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要卸载以下 ${selectedApps.value.length} 个软件吗？\n${selectedApps.value.map(a => a.name).join(', ')}`,
      '确认卸载',
      { confirmButtonText: '卸载', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  operating.value = true
  try {
    await store.uninstallApps(selectedApps.value.map(a => a.name))
    ElMessage.success(`成功卸载 ${selectedApps.value.length} 个软件`)
  } catch (e: unknown) {
    ElMessage.error('卸载失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    operating.value = false
    selectedApps.value = []
  }
}

async function handleBatchUnhold() {
  if (selectedApps.value.length === 0) {
    ElMessage.warning('请先选择要解锁的软件')
    return
  }

  operating.value = true
  try {
    await store.unholdApps(selectedApps.value.map(a => a.name))
    ElMessage.success(`成功解锁 ${selectedApps.value.length} 个软件`)
  } catch (e: unknown) {
    ElMessage.error('解锁失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    operating.value = false
    selectedApps.value = []
  }
}

async function handleToggleHold(app: AppInfo) {
  try {
    await store.toggleHold(app.name, app.held)
    ElMessage.success(app.held ? `已解除锁定：${app.name}` : `已锁定：${app.name}`)
  } catch (e: unknown) {
    ElMessage.error('操作失败：' + (e instanceof Error ? e.message : String(e)))
  }
}

function openVersionDrawer(app: AppInfo) {
  currentApp.value = app
  versionDrawerVisible.value = true
}

function getRowClass({ row }: { row: AppInfo }) {
  if (row.held) return 'held-row'
  if (row.has_update) return 'update-row'
  return ''
}
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <el-icon :size="28" color="#409EFF"><Box /></el-icon>
        <h1>Scoop Easy</h1>
      </div>
      <div class="header-right">
        <el-button :icon="Setting" @click="settingsVisible = true">设置</el-button>
        <el-button :icon="Refresh" :loading="store.loading" @click="store.loadApps">
          刷新
        </el-button>
      </div>
    </el-header>

    <el-container>
      <el-aside width="200px" class="app-aside">
        <el-menu :default-active="currentView" @select="(key: string) => { if (key === 'buckets') { currentView = 'buckets' } else if (key === 'search') { currentView = 'search' } else if (key === 'logs') { currentView = 'logs' } else { currentView = 'apps'; store.filterStatus = key as 'all' | 'updates' | 'held' } }">
          <el-menu-item index="all">
            <template #title>
              <div class="menu-item-content">
                <el-icon><Grid /></el-icon>
                <span>全部软件</span>
                <span class="menu-count">{{ store.apps.length }}</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="updates">
            <template #title>
              <div class="menu-item-content">
                <el-icon><Upload /></el-icon>
                <span>可更新</span>
                <span class="menu-count" :class="{ 'has-update': store.updateCount > 0 }">{{ store.updateCount }}</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="held">
            <template #title>
              <div class="menu-item-content">
                <el-icon><Lock /></el-icon>
                <span>已锁定</span>
                <span class="menu-count held">{{ store.heldCount }}</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="search">
            <template #title>
              <div class="menu-item-content">
                <el-icon><Search /></el-icon>
                <span>搜索安装</span>
              </div>
            </template>
          </el-menu-item>
          <el-divider />
          <el-menu-item index="buckets">
            <template #title>
              <div class="menu-item-content">
                <el-icon><FolderOpened /></el-icon>
                <span>软件桶</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="logs">
            <template #title>
              <div class="menu-item-content">
                <el-icon><Document /></el-icon>
                <span>操作记录</span>
              </div>
            </template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="app-main">
        <template v-if="currentView === 'apps'">
          <div class="toolbar">
            <el-input
              v-model="store.searchQuery"
              placeholder="搜索软件..."
              :prefix-icon="Search"
              clearable
              style="width: 300px"
            />
            <div class="toolbar-actions">
              <el-button
                v-if="store.filterStatus === 'updates'"
                type="primary"
                :icon="Upload"
                :disabled="selectedApps.filter(a => a.has_update && !a.held).length === 0"
                :loading="operating"
                @click="handleBatchUpdate"
              >
                更新选中 ({{ selectedApps.filter(a => a.has_update && !a.held).length }})
              </el-button>
              <el-button
                v-else-if="store.filterStatus === 'held'"
                type="warning"
                :icon="Unlock"
                :disabled="selectedApps.length === 0"
                :loading="operating"
                @click="handleBatchUnhold"
              >
                解锁选中 ({{ selectedApps.length }})
              </el-button>
              <el-button
                v-else
                type="danger"
                :icon="Delete"
                :disabled="selectedApps.length === 0"
                :loading="operating"
                @click="handleBatchUninstall"
              >
                卸载选中 ({{ selectedApps.length }})
              </el-button>
            </div>
          </div>

          <el-table
            v-loading="store.loading"
            :data="store.filteredApps"
            :row-class-name="getRowClass"
            @selection-change="handleSelectionChange"
            style="width: 100%"
            height="calc(100vh - 200px)"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="name" label="软件名称" min-width="180" sortable>
              <template #default="{ row }">
                <span class="app-name">{{ row.name }}</span>
                <el-tag v-if="row.held" type="warning" size="small" style="margin-left: 8px">已锁定</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="版本" min-width="200">
              <template #default="{ row }">
                <span>{{ row.version }}</span>
                <template v-if="row.has_update">
                  <el-icon color="#67C23A" style="margin: 0 8px"><Right /></el-icon>
                  <el-tag type="success" size="small">{{ row.latest_version }}</el-tag>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="bucket" label="Bucket" width="120" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button-group>
                  <el-tooltip content="查看信息">
                    <el-button
                      :icon="InfoFilled"
                      size="small"
                      @click="showAppInfo(row)"
                    />
                  </el-tooltip>
                  <el-tooltip :content="row.held ? '解除锁定' : '锁定（忽略更新）'">
                    <el-button
                      :type="row.held ? 'warning' : 'default'"
                      :icon="row.held ? Unlock : Lock"
                      size="small"
                      @click="handleToggleHold(row)"
                    />
                  </el-tooltip>
                  <el-tooltip content="版本管理">
                    <el-button
                      :icon="Setting"
                      size="small"
                      @click="openVersionDrawer(row)"
                    />
                  </el-tooltip>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <SearchPage v-else-if="currentView === 'search'" />
        <OperationLog v-else-if="currentView === 'logs'" />
        <BucketManager v-else />
      </el-main>
    </el-container>
  </el-container>

  <VersionDrawer
    v-model:visible="versionDrawerVisible"
    :app="currentApp"
  />

  <AppInfoDialog
    v-model:visible="appInfoVisible"
    :app-name="appInfoName"
  />

  <el-dialog v-model="settingsVisible" title="设置" width="400px">
    <el-form label-width="100px">
      <el-form-item label="搜索命令">
        <el-radio-group :model-value="store.settings.search_command" @change="(val: string) => store.saveSettings({ search_command: val as 'scoop' | 'scoop-search' })">
          <el-radio value="scoop">scoop search</el-radio>
          <el-radio value="scoop-search">scoop-search</el-radio>
        </el-radio-group>
        <div class="setting-tip">
          <p><strong>scoop search</strong>：Scoop 内置搜索，无需额外安装</p>
          <p><strong>scoop-search</strong>：第三方工具，速度更快，需先安装</p>
        </div>
      </el-form-item>
      <el-form-item label="极速模式">
        <el-switch
          :model-value="store.turboMode"
          @change="(val: boolean) => store.saveSettings({ turbo_mode: val })"
        />
        <div class="setting-tip">开启后操作完成不自动刷新，需手动刷新</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button type="primary" @click="settingsVisible = false">确定</el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts">
import { Refresh, Search, Grid, Upload, Lock, Unlock, Right, Setting, Box, FolderOpened, Delete, InfoFilled, Document } from '@element-plus/icons-vue'
export default {
  components: { Refresh, Search, Grid, Upload, Lock, Unlock, Right, Setting, Box, FolderOpened, Delete, InfoFilled, Document }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.app-aside .el-menu {
  border-right: none;
}

.menu-item-content {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.menu-count {
  margin-left: auto;
  background: #909399;
  color: #fff;
  font-size: 12px;
  padding: 0 6px;
  border-radius: 10px;
  min-width: 20px;
  height: 18px;
  line-height: 18px;
  text-align: center;
}

.menu-count.has-update {
  background: #f56c6c;
}

.menu-count.held {
  background: #e6a23c;
}

.app-main {
  background: #f5f7fa;
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

.app-name {
  font-weight: 500;
}

.held-row {
  background-color: #fdf6ec !important;
}

.update-row {
  background-color: #f0f9eb !important;
}

.setting-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
  margin-top: 8px;
}

.setting-tip p {
  margin: 4px 0;
}
</style>
