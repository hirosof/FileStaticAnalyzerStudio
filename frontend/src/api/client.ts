const BASE = '/api'

export interface MagikaDetection {
  label: string
  score: number
  mime_type: string
  group: string
  description: string
  is_text: boolean
  extensions: string[]
}
export interface LibmagicDetection {
  mime: string
  description: string
}
export interface TypeDetection {
  magika: MagikaDetection | null
  libmagic: LibmagicDetection | null
}
export interface PeDetail {
  imphash: string | null
}
export interface DetailData {
  result_schema_version: number
  pe?: PeDetail
}

export interface SpecimenOut {
  sha256: string
  size: number
  analysis_state: string
  file_type: string
  md5: string | null
  sha1: string | null
  crc32: string | null
  ssdeep: string | null
  tlsh: string | null
  type_detection: TypeDetection | null
  detail_data: DetailData | null
  has_detail_data: boolean
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
