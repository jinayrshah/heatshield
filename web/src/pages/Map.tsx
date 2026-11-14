import type { GeoJSONSource, Map as MLMap, MapLayerMouseEvent } from 'maplibre-gl'
import * as maplibregl from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Prefs } from '../App'
import { api, type City, type Level, type Stats } from '../api'
import { BaseMap } from '../components/BaseMap'
import { WorkloadSelect } from '../components/Controls'
import { Card, ErrorBox, Legend, LevelIcon, Loading, RiskBadge } from '../components/ui'
import { ago, clock, dayName, dayOf, LEVEL_LABEL, LEVELS, useLoad, workRest } from '../lib'

const FILL: Record<Level, string> = { safe: '#3f9d5a', caution: '#e3b23c', high: '#e07a2f', extreme: '#b8322a' }

export function MapPage({ prefs }: { prefs: Prefs }) {
  const [cityLoad, retry] = useLoad(() => api.city(prefs.workload, prefs.acclimatised), [prefs.workload, prefs.acclimatised])
  const [shapes, setShapes] = useState<GeoJSON.FeatureCollection | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  useEffect(() => {
    api.wards().then(setShapes, () => setShapes(null))
    api.stats().then(setStats, () => setStats(null))
  }, [])

  return (
    <div className="page">
      <div className="page-head">
        <h1>Mumbai heat map</h1>
        <p className="lede">Heat risk in every BMC ward, hour by hour for today and tomorrow. Focus wards are outlined.</p>
      </div>
      <div className="controls controls-tight">
        <WorkloadSelect prefs={prefs} />
      </div>
      {cityLoad.state === 'loading' && <Loading what="the city forecast" />}
      {cityLoad.state === 'error' && <ErrorBox message={cityLoad.message} retry={retry} />}
      {cityLoad.state === 'ready' && shapes && <CityView city={cityLoad.data} shapes={shapes} />}
      {stats && <StatsCard stats={stats} />}
    </div>
  )
}

function defaultIndex(times: string[]): number {
  const now = Date.now()
  const i = times.findIndex((t) => Date.parse(t) <= now && now < Date.parse(t) + 3600000)
  return i >= 0 ? i : 0
}

/** Hour with the highest city-average heat stress on the same day as `from`. */
function peakIndex(city: City, from: number): number {
  const day = dayOf(city.times[from])
  let best = from
  let bestAvg = -Infinity
  city.times.forEach((t, i) => {
    if (dayOf(t) !== day) return
    const vals = city.wards.map((w) => w.wbgt_c[i]).filter((v): v is number => v !== null)
    const avg = vals.reduce((a, b) => a + b, 0) / (vals.length || 1)
    if (avg > bestAvg) {
      bestAvg = avg
      best = i
    }
  })
  return best
}

function CityView({ city, shapes }: { city: City; shapes: GeoJSON.FeatureCollection }) {
  const [idx, setIdx] = useState(() => defaultIndex(city.times))
  const [selected, setSelected] = useState<string | null>(null)
  const mapRef = useRef<MLMap | null>(null)
  const today = dayOf(city.times[0])

  const data = useMemo<GeoJSON.FeatureCollection>(() => {
    const byWard = new Map(city.wards.map((w) => [w.ward, w]))
    return {
      type: 'FeatureCollection',
      features: shapes.features.map((f) => {
        const w = byWard.get(String(f.properties?.ward))
        return { ...f, properties: { ...f.properties, level: w?.level[idx] ?? 'safe', wbgt: w?.wbgt_c[idx] ?? null } }
      }),
    }
  }, [city, shapes, idx])

  useEffect(() => {
    const src = mapRef.current?.getSource('wards') as GeoJSONSource | undefined
    src?.setData(data)
  }, [data])

  useEffect(() => {
    const map = mapRef.current
    if (map?.getLayer('wards-selected')) map.setFilter('wards-selected', ['==', ['get', 'ward'], selected ?? ''])
  }, [selected])

  const onReady = (map: MLMap) => {
    mapRef.current = map
    map.addSource('wards', { type: 'geojson', data })
    map.addLayer({
      id: 'wards-fill',
      type: 'fill',
      source: 'wards',
      paint: { 'fill-color': ['match', ['get', 'level'], 'caution', FILL.caution, 'high', FILL.high, 'extreme', FILL.extreme, FILL.safe], 'fill-opacity': 0.7 },
    })
    map.addLayer({ id: 'wards-line', type: 'line', source: 'wards', paint: { 'line-color': '#ffffff', 'line-width': 1.5 } })
    map.addLayer({ id: 'wards-focus', type: 'line', source: 'wards', filter: ['==', ['get', 'focus'], true], paint: { 'line-color': '#2b1d14', 'line-width': 2.5, 'line-dasharray': [2, 1] } })
    map.addLayer({ id: 'wards-selected', type: 'line', source: 'wards', filter: ['==', ['get', 'ward'], ''], paint: { 'line-color': '#2b1d14', 'line-width': 4 } })
    map.addLayer({
      id: 'wards-label',
      type: 'symbol',
      source: 'wards',
      layout: { 'text-field': ['get', 'ward'], 'text-size': 12, 'text-font': ['Open Sans Bold'] },
      paint: { 'text-color': '#2b1d14', 'text-halo-color': '#fff', 'text-halo-width': 1.5 },
    })
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 })
    map.on('mousemove', 'wards-fill', (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties
      if (!p) return
      map.getCanvas().style.cursor = 'pointer'
      popup
        .setLngLat(e.lngLat)
        .setHTML(`<strong>${p.ward} ward</strong><br>${p.areas}<br>${LEVEL_LABEL[p.level as Level]}, ${p.wbgt === null ? '' : Number(p.wbgt).toFixed(1) + '°'}`)
        .addTo(map)
    })
    map.on('mouseleave', 'wards-fill', () => {
      map.getCanvas().style.cursor = ''
      popup.remove()
    })
    map.on('click', 'wards-fill', (e: MapLayerMouseEvent) => setSelected(String(e.features?.[0]?.properties?.ward ?? '')))
  }

  const ranked = [...city.wards].sort((a, b) => (b.wbgt_c[idx] ?? -99) - (a.wbgt_c[idx] ?? -99))
  const counts = LEVELS.map((l) => ({ l, n: city.wards.filter((w) => w.level[idx] === l).length }))
  const time = city.times[idx]
  const focusWard = city.wards.find((w) => w.ward === selected)

  return (
    <>
      <Card className="map-card">
        <div className="slider">
          <div className="slider-head">
            <label htmlFor="hour" className="field-label">
              {dayName(dayOf(time), today)} {clock(time)}
            </label>
            <div className="btn-row">
              <button className="btn btn-quiet" onClick={() => setIdx(defaultIndex(city.times))}>Now</button>
              <button className="btn btn-quiet" onClick={() => setIdx(peakIndex(city, idx))}>Peak of the day</button>
            </div>
          </div>
          <input id="hour" type="range" min={0} max={city.times.length - 1} value={idx} onChange={(e) => setIdx(Number(e.target.value))} />
          <div className="slider-ticks" aria-hidden="true">
            <span>Today 00:00</span><span>12:00</span><span>Tomorrow 00:00</span><span>12:00</span><span>24:00</span>
          </div>
        </div>
        <div className="map-wrap">
          <BaseMap center={[72.875, 19.075]} zoom={10} onReady={onReady} />
          <div className="map-legend"><Legend /><span className="focus-key">- - Focus ward</span></div>
        </div>
        <p className="hint">{city.resolution_note} Updated {ago(city.fetched_at)}.</p>
        <div className="countrow">
          {counts.map(({ l, n }) => (
            <span key={l} className="count"><span className={`swatch lv-${l}`}><LevelIcon level={l} size={12} /></span>{n} {LEVEL_LABEL[l].toLowerCase()}</span>
          ))}
        </div>
      </Card>

      {focusWard && (
        <Card title={`${focusWard.ward} ward · ${focusWard.areas}`} aside={<button className="btn btn-quiet" onClick={() => setSelected(null)}>Close</button>}>
          <p>
            At {clock(time)}: <RiskBadge level={focusWard.level[idx] ?? 'safe'} /> heat stress {focusWard.wbgt_c[idx]?.toFixed(1)}°. {workRest(focusWard.work_min[idx] ?? 60)}.
          </p>
          <a className="btn" href="#/check" onClick={() => localStorage.setItem('hs.place', JSON.stringify({ label: `${focusWard.areas.split(',')[0]}, Mumbai (${focusWard.ward} ward)`, lat: focusWard.lat, lon: focusWard.lon }))}>
            See this ward hour by hour
          </a>
        </Card>
      )}

      <Card title={`Hotspots at ${clock(time)}`}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Ward</th><th>Areas</th><th>Risk</th><th className="num">Heat stress</th></tr></thead>
            <tbody>
              {ranked.map((w, i) => (
                <tr key={w.ward} className={w.ward === selected ? 'row-on' : ''} onClick={() => setSelected(w.ward)}>
                  <td>{i + 1}</td>
                  <td><strong>{w.ward}</strong>{w.focus && <span className="tag">focus</span>}</td>
                  <td>{w.areas}</td>
                  <td>{w.level[idx] && <RiskBadge level={w.level[idx]!} />}</td>
                  <td className="num">{w.wbgt_c[idx]?.toFixed(1)}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}

function StatsCard({ stats }: { stats: Stats }) {
  const alerts = Object.values(stats.alerts).reduce((a, b) => a + b, 0)
  return (
    <Card title="HeatShield in use">
      <div className="tiles">
        <div className="tile"><span className="tile-label">People signed up</span><span className="tile-value">{stats.users.toLocaleString('en-IN')}</span></div>
        <div className="tile"><span className="tile-label">Getting alerts</span><span className="tile-value">{stats.active_users.toLocaleString('en-IN')}</span></div>
        <div className="tile"><span className="tile-label">Alerts sent</span><span className="tile-value">{alerts.toLocaleString('en-IN')}</span></div>
        <div className="tile"><span className="tile-label">Delivered</span><span className="tile-value">{stats.delivery_rate === null ? '–' : `${Math.round(stats.delivery_rate * 100)}%`}</span></div>
      </div>
      <p className="hint">Totals only. No personal data is shown.</p>
    </Card>
  )
}
