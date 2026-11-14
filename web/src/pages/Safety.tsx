import type { Map as MLMap } from 'maplibre-gl'
import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import type { Prefs } from '../App'
import { api, type Safety, type WaterPoint } from '../api'
import { BaseMap } from '../components/BaseMap'
import { LocationPicker } from '../components/LocationPicker'
import { Card, ErrorBox, LevelIcon, Loading } from '../components/ui'
import { useLoad } from '../lib'

export function SafetyPage({ prefs }: { prefs: Prefs }) {
  const [load, retry] = useLoad(() => api.safety(), [])
  return (
    <div className="page">
      <div className="page-head">
        <h1>Feeling unwell in the heat?</h1>
        <p className="lede">Answer one question at a time. If in doubt, call for help.</p>
      </div>
      <div className="call-row">
        <a className="btn btn-danger btn-big" href="tel:108">Call 108 ambulance</a>
        <a className="btn btn-big" href="tel:112">Call 112 emergency</a>
      </div>
      {load.state === 'loading' && <Loading what="first aid" />}
      {load.state === 'error' && <ErrorBox message={load.message} retry={retry} />}
      {load.state === 'ready' && <SymptomCheck safety={load.data} />}
      <WaterNearMe prefs={prefs} />
    </div>
  )
}

function SymptomCheck({ safety }: { safety: Safety }) {
  const [step, setStep] = useState(0)
  const [result, setResult] = useState<number | null>(null)
  const reset = () => {
    setStep(0)
    setResult(null)
  }

  if (result === -1) {
    return (
      <Card className="result lv-tint-safe" aside={<button className="btn btn-quiet" onClick={reset}>Start again</button>}>
        <h2 className="result-title"><LevelIcon level="safe" size={24} /> No warning signs right now.</h2>
        <ol className="steps">
          <li>Keep drinking water, about a cup every 20 minutes in the heat.</li>
          <li>Take your breaks in shade, and follow the work and rest times on the Heat now page.</li>
          <li>Check again if anything changes. Signs can appear quickly.</li>
        </ol>
      </Card>
    )
  }

  if (result !== null) {
    const r = safety.flow[result].result
    return (
      <Card className={`result lv-tint-${r.severity}`} aside={<button className="btn btn-quiet" onClick={reset}>Start again</button>}>
        <h2 className="result-title"><LevelIcon level={r.severity} size={24} /> {r.title}</h2>
        {r.call && <a className="btn btn-danger btn-big" href="tel:108">Call 108 now</a>}
        <ol className="steps">{r.steps.map((s) => <li key={s}>{s}</li>)}</ol>
      </Card>
    )
  }

  const q = safety.flow[step]
  const last = step === safety.flow.length - 1
  return (
    <Card title={`Question ${step + 1} of ${safety.flow.length}`}>
      <p className="question">{q.question}</p>
      <ul className="signs">{q.signs.map((s) => <li key={s}>{s}</li>)}</ul>
      <div className="btn-row">
        <button className="btn btn-primary" onClick={() => setResult(step)}>Yes</button>
        <button className="btn" onClick={() => (last ? setResult(-1) : setStep(step + 1))}>No</button>
      </div>
    </Card>
  )
}

const KIND_LABEL: Record<string, string> = { water: 'Drinking water', shelter: 'Shelter', hospital: 'Hospital' }
const KIND_COLOR: Record<string, string> = { water: '#2a78d6', shelter: '#6b5a4a', hospital: '#b8322a' }

function WaterNearMe({ prefs }: { prefs: Prefs }) {
  const [points, setPoints] = useState<WaterPoint[] | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const { place } = prefs

  useEffect(() => {
    let live = true
    setBusy(true)
    setError('')
    api.water(place.lat, place.lon).then(
      (r) => live && setPoints(r.points),
      (e: Error) => live && (setPoints(null), setError(e.message)),
    ).finally(() => live && setBusy(false))
    map.current?.flyTo({ center: [place.lon, place.lat], zoom: 14 })
    return () => {
      live = false
    }
  }, [place.lat, place.lon])

  useEffect(() => {
    markers.current.forEach((m) => m.remove())
    markers.current = []
    if (!map.current || !points) return
    for (const p of points) {
      const el = document.createElement('span')
      el.className = 'pin'
      el.style.background = KIND_COLOR[p.kind] ?? '#555'
      el.title = `${KIND_LABEL[p.kind]}${p.name ? `: ${p.name}` : ''}`
      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).setPopup(new maplibregl.Popup({ offset: 10 }).setText(el.title)).addTo(map.current))
    }
  }, [points])

  const counts = (k: string) => points?.filter((p) => p.kind === k).length ?? 0
  return (
    <Card title="Water, shade and hospitals near you">
      <LocationPicker value={place} onChange={prefs.setPlace} />
      <div className="map-wrap">
        <BaseMap className="map map-small" center={[place.lon, place.lat]} zoom={14} onReady={(m) => { map.current = m; setPoints((p) => (p ? [...p] : p)) }} />
      </div>
      {busy && <p className="hint">Looking up places within 1.5 km…</p>}
      {error && <p className="hint">{error}</p>}
      {points && (
        <p className="hint">
          Within 1.5 km: {counts('water')} drinking water points, {counts('shelter')} shelters, {counts('hospital')} hospitals, from OpenStreetMap. Many taps and shelters are not mapped yet, so also ask nearby shops and offices.
        </p>
      )}
      <ul className="legend">
        {Object.entries(KIND_LABEL).map(([k, v]) => <li key={k}><span className="pin pin-key" style={{ background: KIND_COLOR[k] }} />{v}</li>)}
      </ul>
    </Card>
  )
}
