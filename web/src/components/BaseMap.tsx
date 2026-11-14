import * as maplibregl from 'maplibre-gl'
import type { Map as MLMap, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
// Bundle MapLibre's worker (and the code it imports) as its own file and tell
// MapLibre where it is; by default it looks next to its own module, which does
// not exist after bundling.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

maplibregl.setWorkerUrl(workerUrl)

// OpenStreetMap raster tiles: free and keyless. For heavy public traffic,
// switch to a hosted tile service per the OSM tile usage policy.
const STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
    },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#ece6dc' } },
    { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.6, 'raster-opacity': 0.85 } },
  ],
}

export function BaseMap({ center, zoom, onReady, className = 'map' }: { center: [number, number]; zoom: number; onReady: (m: MLMap) => void; className?: string }) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const map = new maplibregl.Map({ container: el.current!, style: STYLE, center, zoom, attributionControl: { compact: true }, cooperativeGestures: true })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('load', () => onReady(map))
    return () => map.remove()
    // The map is created once; callers update it through the instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return <div ref={el} className={className} />
}
