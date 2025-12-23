<script setup lang="ts">
import { ref, watch } from 'vue'
import * as api from '../api'

const props = defineProps<{
  visible: boolean
  appName: string | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const manifest = ref<string>('')
const loading = ref(false)

watch(() => props.visible, async (val) => {
  if (val && props.appName) {
    loading.value = true
    manifest.value = ''
    try {
      const data = await api.getAppInfo(props.appName)
      manifest.value = JSON.stringify(data, null, 2)
    } catch {
      manifest.value = '无法获取软件清单'
    } finally {
      loading.value = false
    }
  }
})

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="`软件清单 - ${appName}`"
    width="700px"
    @close="close"
  >
    <div v-loading="loading" class="manifest-container">
      <pre class="manifest-content">{{ manifest }}</pre>
    </div>
    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.manifest-container {
  max-height: 500px;
  overflow: auto;
}

.manifest-content {
  margin: 0;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
