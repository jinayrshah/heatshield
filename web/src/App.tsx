import { lazy, Suspense, useEffect, useState } from 'react'
import { api, type Meta, type Place, type Workload } from './api'
import { useStored } from './lib'
import { CheckPage } from './pages/Check'
import { PlanPage } from './pages/Plan'
import { AlertsPage } from './pages/Alerts'
import { AboutPage } from './pages/About'
import { Loading } from './components/ui'

// The map library is large, so pages that use it load on demand.
const MapPage = lazy(() => import('./pages/Map').then((m) => ({ default: m.MapPage })))
const SafetyPage = lazy(() => import('./pages/Safety').then((m) => ({ default: m.SafetyPage })))

export const DEFAULT_PLACE: Place = { label: 'Kurla, Mumbai (L ward)', lat: 19.0876, lon: 72.8867 }

export interface Prefs {
  place: Place
  workload: Workload
  acclimatised: boolean
  setPlace: (p: Place) => void
  setWorkload: (w: Workload) => void
  setAcclimatised: (a: boolean) => void
  meta: Meta | null
}

const PAGES = [
  { id: 'check', label: 'Heat now', icon: 'M10 2v2M10 16v2M2 10h2M16 10h2M4.300 4.300l1.400 1.400M14.300 14.300l1.400 1.400M4.300 15.700l1.400-1.400M14.300 5.700l1.400-1.400M10 6.500a3.500 3.500 0 1 0 0 7 3.500 3.500 0 0 0 0-7z' },
  { id: 'plan', label: 'Plan a job', icon: 'M3 5h14v12H3zM3 9h14M7 3v4M13 3v4' },
  { id: 'map', label: 'City map', icon: 'M2 5l5-2 6 2 5-2v12l-5 2-6-2-5 2zM7 3v12M13 5v12' },
  { id: 'safety', label: 'Feeling unwell', icon: 'M10 17s-7-4.300-7-9a3.800 3.800 0 0 1 7-2 3.800 3.800 0 0 1 7 2c0 4.700-7 9-7 9zM10 7v4M8 9h4' },
  { id: 'alerts', label: 'My alerts', icon: 'M10 2.500a5 5 0 0 0-5 5v3l-1.500 3h13L15 10.500v-3a5 5 0 0 0-5-5zM8 16a2 2 0 0 0 4 0' },
  { id: 'about', label: 'About', icon: 'M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM10 9v5M10 6v.100' },
] as const
type PageId = (typeof PAGES)[number]['id']

function pageFromHash(): PageId {
  const id = location.hash.replace(/^#\/?/, '')
  return (PAGES.find((p) => p.id === id)?.id ?? 'check') as PageId
}

export default function App() {
  const [page, setPage] = useState<PageId>(pageFromHash)
  const [place, setPlace] = useStored<Place>('hs.place', DEFAULT_PLACE)
  const [workload, setWorkload] = useStored<Workload>('hs.workload', 'heavy')
  const [acclimatised, setAcclimatised] = useStored<boolean>('hs.acclimatised', true)
  const [meta, setMeta] = useState<Meta | null>(null)

  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    api.meta().then(setMeta, () => setMeta(null))
  }, [])

  const prefs: Prefs = { place, workload, acclimatised, setPlace, setWorkload, setAcclimatised, meta }

  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <a className="brand" href="#/check" aria-label="HeatShield home">
          <img src="/favicon.svg" alt="" width="30" height="30" />
          <span>HeatShield</span>
        </a>
        <nav className="nav" aria-label="Main">
          {PAGES.map((p) => (
            <a key={p.id} href={`#/${p.id}`} className={page === p.id ? 'active' : ''} aria-current={page === p.id ? 'page' : undefined}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.800" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d={p.icon} />
              </svg>
              <span>{p.label}</span>
            </a>
          ))}
        </nav>
        <a className="sos" href="tel:108" title="Call 108 ambulance">
          Emergency 108
        </a>
      </header>
      {meta?.sample_data && (
        <div className="banner" role="status">
          Demo mode: showing a recorded forecast from 14 Nov 2026, not today's live weather.
        </div>
      )}
      <main id="main" className="main">
        {page === 'check' && <CheckPage prefs={prefs} />}
        {page === 'plan' && <PlanPage prefs={prefs} />}
        <Suspense fallback={<Loading what="the page" />}>
          {page === 'map' && <MapPage prefs={prefs} />}
          {page === 'safety' && <SafetyPage prefs={prefs} />}
        </Suspense>
        {page === 'alerts' && <AlertsPage prefs={prefs} />}
        {page === 'about' && <AboutPage />}
      </main>
      <footer className="footer">
        Guidance based on NIOSH and ISO 7243 heat limits. Not medical advice. In an emergency call <a href="tel:108">108</a> or <a href="tel:112">112</a>.
        <br />
        Weather: <a href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo</a> (CC BY 4.0). Ward boundaries: DataMeet (CC BY-SA 2.5 IN). Map data © OpenStreetMap contributors.
      </footer>
    </div>
  )
}
