const BASE = 'http://localhost:8000'

export interface SpecimenOut {
  sha256: string
  size: number
  analysis_state: string
  file_type: string
}

export interface ItemStatus {
  request_item_id: string
  request_reception_id: string
  original_name: string | null
  process_state: string
  current_phase: string | null
  error_type: string | null
  sha256: string | null
  specimen: SpecimenOut | null
}

export interface JobEventOut {
  ts: string
  level: string
  phase: string | null
  message: string
}

export async function submitFile(
  file: File,
): Promise<{ request_reception_id: string; request_item_id: string }> {
  const fd = new FormData()
  fd.append('file', file) // バックエンドの UploadFile 引数名 "file" に対応
  const res = await fetch(`${BASE}/submit`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error(`submit failed: ${res.status}`)
  return res.json()
}

export async function getItem(id: string): Promise<ItemStatus> {
  const res = await fetch(`${BASE}/items/${id}`)
  if (!res.ok) throw new Error(`getItem failed: ${res.status}`)
  return res.json()
}

export async function getItemEvents(id: string): Promise<JobEventOut[]> {
  const res = await fetch(`${BASE}/items/${id}/events`)
  if (!res.ok) throw new Error(`events failed: ${res.status}`)
  return res.json()
}
