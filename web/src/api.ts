export type Level = 'safe' | 'caution' | 'high' | 'extreme'
export type Workload = 'light' | 'moderate' | 'heavy' | 'very_heavy'

export interface Hour {
  time: string
  air_c: number
  rh_pct: number
  wind_ms: number
  solar_wm2: number
  globe_c: number
  wbgt_c: number
  limit_c: number
  level: Level
  work_min: number
  rest_min: number
}
export interface Range { start: string; end: string; level: Level }
export interface Day {
  date: string
  level: Level
  peak_wbgt_c: number
  peak_time: string
  max_air_c: number
  dangerous: Range[]
  caution: Range[]
  night_min_air_c: number | null
  warm_night: boolean
  advice: string
  water: string
}
export interface LocationMeta {
  lat: number; lon: number; tz: string
  ward: string | null; ward_areas: string | null
  fetched_at: string; source: string; stale: boolean
}
export interface Forecast { location: LocationMeta; now: Hour | null; days: Day[]; hours: Hour[] }
export interface PlanWindow { start: string; end: string; level: Level; work_min: number; total_min: number; peak_wbgt_c: number }
export interface Plan { day: string; duration_hours: number; windows: PlanWindow[] }
export interface Ward {
  ward: string; areas: string; focus: boolean; lat: number; lon: number
  wbgt_c: (number | null)[]; level: (Level | null)[]; work_min: (number | null)[]
}
export interface City { times: string[]; wards: Ward[]; fetched_at: string; source: string; stale: boolean; resolution_note: string }
export interface Meta {
  version: string
  sample_data: boolean
  workloads: { id: Workload; label: string; examples: string }[]
  levels: { id: Level; label: string; advice: string; water: string }[]
  channels: { web: boolean; telegram: boolean; whatsapp: boolean }
  warm_night_c: number
}
export interface Place { label: string; lat: number; lon: number }
export interface User {
  id: number; name: string; area_label: string; lat: number; lon: number; tz: string
  workload: Workload; work_start: number; work_end: number
  new_to_heat: boolean; new_to_heat_until: string | null
  paused: boolean; morning_alerts: boolean; peak_reminders: boolean; warm_night_alerts: boolean
  telegram: { connected: boolean; available: boolean; link: string | null }
  whatsapp: { number: string; available: boolean }
}
export interface AlertItem { id: number; kind: string; level: Level; title: string; body: string; created_at: string; deliveries: Record<string, string> }
export interface SafetyStep {
  id: string; question: string; signs: string[]
  result: { title: string; severity: Level; call: boolean; steps: string[] }
}
export interface Safety { emergency_numbers: { number: string; label: string }[]; flow: SafetyStep[] }
export interface Stats {
  users: number; active_users: number
  alerts: Record<string, number>; deliveries: Record<string, number>; delivery_rate: number | null
}
export interface WaterPoint { kind: 'water' | 'shelter' | 'hospital'; name: string; lat: number; lon: number }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Params = Record<string, string | number | boolean | undefined>

async function request<T>(method: string, path: string, opts: { params?: Params; body?: unknown; token?: string } = {}): Promise<T> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(opts.params ?? {})) if (v !== undefined) qs.set(k, String(v))
  const headers: Record<string, string> = {}
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`
  let resp: Response
  try {
    resp = await fetch(`/api${path}${qs.size ? `?${qs}` : ''}`, {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Could not reach HeatShield. Check your internet connection and try again.')
  }
  if (resp.status === 204) return undefined as T
  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    const detail = data?.detail
    const message =
      typeof detail === 'string' ? detail
      : Array.isArray(detail) && detail[0]?.msg ? String(detail[0].msg).replace(/^Value error, /, '')
      : 'Something went wrong. Please try again.'
    throw new ApiError(resp.status, message)
  }
  return data as T
}

export const api = {
  meta: () => request<Meta>('GET', '/meta'),
  forecast: (lat: number, lon: number, workload: Workload, acclimatised: boolean) =>
    request<Forecast>('GET', '/forecast', { params: { lat, lon, workload, acclimatised, days: 7 } }),
  plan: (p: { lat: number; lon: number; workload: Workload; acclimatised: boolean; duration_hours: number; day: string; earliest_hour: number; latest_hour: number }) =>
    request<Plan>('GET', '/plan', { params: p }),
  city: (workload: Workload, acclimatised: boolean) => request<City>('GET', '/city', { params: { workload, acclimatised } }),
  wards: () => request<GeoJSON.FeatureCollection>('GET', '/wards.geojson'),
  geocode: (q: string) => request<{ results: Place[]; remote_ok: boolean }>('GET', '/geocode', { params: { q } }),
  water: (lat: number, lon: number) => request<{ points: WaterPoint[]; attribution: string }>('GET', '/water', { params: { lat, lon } }),
  safety: () => request<Safety>('GET', '/safety'),
  stats: () => request<Stats>('GET', '/stats'),
  signUp: (body: Record<string, unknown>) => request<{ token: string; user: User }>('POST', '/users', { body }),
  me: (token: string) => request<User>('GET', '/me', { token }),
  updateMe: (token: string, body: Record<string, unknown>) => request<User>('PATCH', '/me', { token, body }),
  deleteMe: (token: string) => request<void>('DELETE', '/me', { token }),
  myAlerts: (token: string) => request<{ alerts: AlertItem[] }>('GET', '/me/alerts', { token }),
  previewAlert: (token: string) => request<{ id: number; deliveries: Record<string, string> }>('POST', '/me/alerts/preview', { token }),
}
