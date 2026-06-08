<script setup lang="ts">
import { ref } from 'vue'
import FileUpload, { type FileUploadUploaderEvent } from 'primevue/fileupload'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { submitFile, getItem, getItemEvents, type ItemStatus, type JobEventOut } from './api/client'

const status = ref<ItemStatus | null>(null)
const events = ref<JobEventOut[]>([])
const busy = ref(false)
const errorMsg = ref('')

const TERMINAL = ['Completed', 'Error']

function severityOf(state: string): string {
  switch (state) {
    case 'Completed':
      return 'success'
    case 'Error':
      return 'danger'
    case 'Processing':
      return 'info'
    default:
      return 'secondary' // Pending 等
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

// PrimeVue FileUpload (customUpload) のアップロードイベント
async function onUpload(event: FileUploadUploaderEvent) {
  const file = Array.isArray(event.files) ? event.files[0] : event.files
  if (!file) return

  // 以下は従来どおり（errorMsg/status/events リセット → submitFile → ポーリング …）
  errorMsg.value = ''
  status.value = null
  events.value = []
  busy.value = true
  try {
    const { request_item_id } = await submitFile(file)
    // 終端状態になるまでポーリング
    for (;;) {
      const s = await getItem(request_item_id)
      status.value = s
      if (TERMINAL.includes(s.process_state)) break
      await sleep(800)
    }
    events.value = await getItemEvents(request_item_id)
  } catch (e) {
    errorMsg.value = String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div style="max-width: 900px; margin: 2rem auto; padding: 0 1rem">
    <h1>FileStaticAnalyzerStudio</h1>

    <FileUpload
      mode="basic"
      customUpload
      auto
      :multiple="false"
      chooseLabel="ファイルを選択して解析"
      @uploader="onUpload"
    />

    <p v-if="busy" style="margin-top: 1rem"><i class="pi pi-spin pi-spinner" /> 解析中...</p>
    <p v-if="errorMsg" style="color: #e24c4c">{{ errorMsg }}</p>

    <div v-if="status" style="margin-top: 1.5rem">
      <h2>結果</h2>
      <p>
        <strong>状態：</strong>
        <Tag :value="status.process_state" :severity="severityOf(status.process_state)" />
        <span v-if="status.current_phase"> （{{ status.current_phase }}）</span>
      </p>
      <p><strong>ファイル名：</strong>{{ status.original_name }}</p>
      <p v-if="status.sha256">
        <strong>SHA256：</strong><code>{{ status.sha256 }}</code>
      </p>
      <p v-if="status.error_type" style="color: #e24c4c">
        <strong>エラー種別：</strong>{{ status.error_type }}
      </p>

      <div v-if="status.specimen">
        <p><strong>サイズ：</strong>{{ status.specimen.size }} bytes</p>
        <p><strong>種別：</strong>{{ status.specimen.file_type }}</p>
        <p><strong>検体の解析状態：</strong>{{ status.specimen.analysis_state }}</p>
      </div>

      <h3 style="margin-top: 1.5rem">イベントログ</h3>
      <DataTable :value="events" size="small" stripedRows>
        <Column field="ts" header="時刻" />
        <Column field="level" header="level" />
        <Column field="phase" header="phase" />
        <Column field="message" header="message" />
      </DataTable>
    </div>
  </div>
</template>
<style scoped></style>
