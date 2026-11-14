import { useEffect, useState } from 'react'
import type { Level, Range } from './api'

export const LEVELS: Level[] = ['safe', 'caution', 'high', 'extreme']
export const LEVEL_LABEL: Record<Level, string> = { safe: 'Safe', caution: 'Caution', high: 'High', extreme: 'Extreme' }

// API times are ISO strings already in the location's own timezone
// ("2026-11-14T13:00:00+05:30"), so the wall-clock parts are read straight
// from the text. Passing them through Date would shift them to the viewer's
// timezone, which is wrong when checking another city.
export const clock = (iso: string) => iso.slice(11, 16)
export const dayOf = (iso: string) => iso.slice(0, 10)
export const hourOf = (iso: string) => Number(iso.slice(11, 13))
export const endClock = (iso: string) => (clock(iso) === '00:00' ? 'midnight' : clock(iso))
export const rangeText = (ranges: Range[]) => ranges.map((r) => `${clock(r.start)} to ${endClock(r.end)}`).join(', ')

const DAY_FMT = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'short', timeZone: 'UTC' })
const SHORT_FMT = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', timeZone: 'UTC' })

export function dayName(date: string, today: string, short = false): string {
  const diff = Math.round((Date.parse(date) - Date.parse(today)) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return (short ? SHORT_FMT : DAY_FMT).format(new Date(`${date}T00:00:00Z`))
}

export function hourLabel(h: number): string {
  return `${String(h % 24).padStart(2, '0')}:00`
}

export function workRest(work: number): string {
  if (work >= 60) return 'Work the full hour'
  if (work <= 0) return 'Stop this work'
  return `${work} min work, ${60 - work} min rest`
}

export function ago(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  return `${Math.round(hours / 24)} d ago`
}

export function useStored<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key)
      return raw === null ? initial : (JSON.parse(raw) as T)
    } catch {
      return initial
    }
  })
  const set = (v: T) => {
    setValue(v)
    try {
      if (v === null || v === undefined) localStorage.removeItem(key)
      else localStorage.setItem(key, JSON.stringify(v))
    } catch {
      /* private mode: keep it in memory only */
    }
  }
  return [value, set]
}

export type Load<T> = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; data: T }

/** Fetch on mount and whenever `deps` change; the latest request wins. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]): [Load<T>, () => void] {
  const [load, setLoad] = useState<Load<T>>({ state: 'loading' })
  const [nonce, setNonce] = useState(0)
  useEffect(() => {
    let live = true
    setLoad({ state: 'loading' })
    fn().then(
      (data) => live && setLoad({ state: 'ready', data }),
      (err: Error) => live && setLoad({ state: 'error', message: err.message }),
    )
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])
  return [load, () => setNonce((n) => n + 1)]
}
