import { useEffect, useRef, useState } from 'react'
import { api, type Place } from '../api'

interface Props {
  value: Place
  onChange: (p: Place) => void
}

export function LocationPicker({ value, onChange }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Place[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      setResults(null)
      return
    }
    let live = true
    const timer = setTimeout(() => {
      setBusy(true)
      api
        .geocode(q)
        .then((r) => {
          if (!live) return
          setResults(r.results)
          setNote(r.results.length === 0 ? (r.remote_ok ? 'No place found with that name.' : 'Place search is offline. Mumbai areas still work, or use your location.') : '')
        })
        .catch((e: Error) => live && (setResults([]), setNote(e.message)))
        .finally(() => live && setBusy(false))
    }, 300)
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [query])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const pick = (p: Place) => {
    onChange(p)
    setQuery('')
    setResults(null)
    setOpen(false)
    setNote('')
  }

  const locate = () => {
    if (!navigator.geolocation) {
      setNote('This browser cannot share its location. Type an area instead.')
      return
    }
    setBusy(true)
    setNote('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBusy(false)
        // Rounded to about 1 km before it leaves the device.
        pick({ label: 'My location', lat: Math.round(pos.coords.latitude * 100) / 100, lon: Math.round(pos.coords.longitude * 100) / 100 })
      },
      () => {
        setBusy(false)
        setNote('Could not get your location. Allow location access, or type an area.')
      },
      { timeout: 10000, maximumAge: 600000 },
    )
  }

  return (
    <div className="locpick" ref={box}>
      <label className="field-label" htmlFor="loc-input">
        Place
      </label>
      <div className="locpick-row">
        <div className="locpick-input">
          <input
            id="loc-input"
            type="search"
            autoComplete="off"
            placeholder={value.label}
            value={query}
            onFocus={() => setOpen(true)}
            onChange={(e) => {
              setQuery(e.target.value)
              setOpen(true)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && results?.[0]) pick(results[0])
              if (e.key === 'Escape') setOpen(false)
            }}
            aria-describedby="loc-current"
          />
          {open && results && results.length > 0 && (
            <ul className="locpick-results">
              {results.map((r, i) => (
                <li key={`${r.label}-${i}`}>
                  <button type="button" onClick={() => pick(r)}>
                    {r.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button type="button" className="btn btn-icon" onClick={locate} disabled={busy} title="Use my location" aria-label="Use my location">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="10" cy="10" r="5.500" />
            <path d="M10 1.500v3M10 15.500v3M1.500 10h3M15.500 10h3" />
          </svg>
        </button>
      </div>
      <p className="hint" id="loc-current">
        {note || (busy ? 'Searching…' : `Showing ${value.label}. Type an area or city to change it.`)}
      </p>
    </div>
  )
}
