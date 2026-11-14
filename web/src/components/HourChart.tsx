import { useEffect, useMemo, useRef, useState } from 'react'
import type { Hour } from '../api'
import { clock, hourOf, LEVEL_LABEL, workRest } from '../lib'
import { LevelIcon } from './ui'

const H = 250
const PAD = { top: 18, right: 14, bottom: 58, left: 38 }
const STRIP_Y = H - 46
const STRIP_H = 14

/** Draw in real pixels so text stays readable on phones instead of shrinking with the SVG. */
function useWidth(ref: React.RefObject<HTMLDivElement | null>, fallback = 720): number {
  const [w, setW] = useState(fallback)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(300, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [ref])
  return w
}

/**
 * One day of heat stress: the WBGT line against the limit for the chosen
 * work, with a strip underneath that gives each hour's risk level.
 */
export function HourChart({ hours, nowTime }: { hours: Hour[]; nowTime?: string }) {
  const [active, setActive] = useState<number | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const W = useWidth(box)

  const g = useMemo(() => {
    const values = hours.flatMap((h) => [h.wbgt_c, h.limit_c])
    const lo = Math.floor((Math.min(...values) - 1) / 2) * 2
    const hi = Math.ceil((Math.max(...values) + 1) / 2) * 2
    const innerW = W - PAD.left - PAD.right
    const innerH = STRIP_Y - 12 - PAD.top
    const slot = innerW / 24
    const x = (h: Hour) => PAD.left + (hourOf(h.time) + 0.5) * slot
    const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * innerH
    const ticks: number[] = []
    const step = hi - lo > 12 ? 4 : 2
    for (let v = lo; v <= hi; v += step) ticks.push(v)
    return { lo, hi, slot, x, y, ticks, innerW }
  }, [hours, W])

  if (hours.length === 0) return null
  const limit = hours[0].limit_c
  const line = hours.map((h, i) => `${i ? 'L' : 'M'}${g.x(h).toFixed(1)},${g.y(h.wbgt_c).toFixed(1)}`).join('')
  const base = g.y(g.lo)
  const area = `${line}L${g.x(hours[hours.length - 1]).toFixed(1)},${base}L${g.x(hours[0]).toFixed(1)},${base}Z`
  const peak = hours.reduce((a, b) => (b.wbgt_c > a.wbgt_c ? b : a))
  const nowIdx = nowTime ? hours.findIndex((h) => h.time === nowTime) : -1
  const shown = active !== null ? hours[active] : null

  const onMove = (clientX: number) => {
    const rect = svg.current!.getBoundingClientRect()
    const px = ((clientX - rect.left) / rect.width) * W
    let best = 0
    hours.forEach((h, i) => {
      if (Math.abs(g.x(h) - px) < Math.abs(g.x(hours[best]) - px)) best = i
    })
    setActive(best)
  }

  const limitAbove = g.y(limit) - PAD.top > 26
  return (
    <figure className="chart">
      <div className="chart-plot" ref={box}>
        <svg
          ref={svg}
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Heat stress by hour. Peak ${peak.wbgt_c.toFixed(1)} degrees at ${clock(peak.time)}. Limit for this work ${limit.toFixed(1)} degrees.`}
          onPointerMove={(e) => onMove(e.clientX)}
          onPointerDown={(e) => onMove(e.clientX)}
          onPointerLeave={() => setActive(null)}
        >
          {g.ticks.map((v) => (
            <g key={v}>
              <line className="grid" x1={PAD.left} x2={W - PAD.right} y1={g.y(v)} y2={g.y(v)} />
              <text className="tick" x={PAD.left - 8} y={g.y(v) + 4} textAnchor="end">{v}°</text>
            </g>
          ))}
          <path className="wbgt-area" d={area} />
          <line className="limit" x1={PAD.left} x2={W - PAD.right} y1={g.y(limit)} y2={g.y(limit)} />
          <text className="limit-label" x={W - PAD.right} y={g.y(limit) + (limitAbove ? -7 : 16)} textAnchor="end">
            {W < 520 ? 'Limit' : 'Limit for this work'} {limit.toFixed(1)}°
          </text>
          <path className="wbgt-line" d={line} />
          {nowIdx >= 0 && (
            <g>
              <line className="now-line" x1={g.x(hours[nowIdx])} x2={g.x(hours[nowIdx])} y1={PAD.top} y2={STRIP_Y + STRIP_H} />
              <text className="now-label" x={g.x(hours[nowIdx])} y={PAD.top - 5} textAnchor="middle">Now</text>
            </g>
          )}
          <circle className="dot" cx={g.x(peak)} cy={g.y(peak.wbgt_c)} r="5" />
          <text className="peak-label" x={Math.min(Math.max(g.x(peak), PAD.left + 40), W - PAD.right - 40)} y={g.y(peak.wbgt_c) - 11} textAnchor="middle">
            Peak {peak.wbgt_c.toFixed(1)}°
          </text>
          {hours.map((h) => (
            <rect key={h.time} className={`cell lv-fill-${h.level}`} x={g.x(h) - g.slot / 2 + 1} y={STRIP_Y} width={g.slot - 2} height={STRIP_H} rx="3" />
          ))}
          {(W < 520 ? [0, 6, 12, 18] : [0, 3, 6, 9, 12, 15, 18, 21]).map((hr) => (
            <text key={hr} className="tick" x={PAD.left + (hr + 0.5) * g.slot} y={H - 12} textAnchor="middle">
              {String(hr).padStart(2, '0')}:00
            </text>
          ))}
          {shown && (
            <g>
              <line className="cross" x1={g.x(shown)} x2={g.x(shown)} y1={PAD.top} y2={STRIP_Y + STRIP_H} />
              <circle className="dot" cx={g.x(shown)} cy={g.y(shown.wbgt_c)} r="5" />
            </g>
          )}
        </svg>
        {shown && (
          <div className="tip" style={{ left: `${(g.x(shown) / W) * 100}%`, transform: `translateX(${g.x(shown) > W * 0.6 ? 'calc(-100% - 12px)' : '12px'})` }}>
            <strong>{clock(shown.time)}</strong>
            <span className="tip-level">
              <span className={`swatch lv-${shown.level}`}><LevelIcon level={shown.level} size={12} /></span>
              {LEVEL_LABEL[shown.level]}
            </span>
            <span>Heat stress {shown.wbgt_c.toFixed(1)}°</span>
            <span>{workRest(shown.work_min)}</span>
            <span className="tip-muted">Air {shown.air_c.toFixed(0)}°, humidity {shown.rh_pct}%</span>
          </div>
        )}
      </div>
      <figcaption>Heat stress (WBGT, °C) through the day. The strip under the line is the risk level for each hour.</figcaption>
    </figure>
  )
}

export function HourTable({ hours }: { hours: Hour[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Time</th><th>Risk</th><th className="num">Heat stress</th><th>Each hour</th><th className="num">Air</th><th className="num">Humidity</th></tr>
        </thead>
        <tbody>
          {hours.map((h) => (
            <tr key={h.time}>
              <td>{clock(h.time)}</td>
              <td><span className="tip-level"><span className={`swatch lv-${h.level}`}><LevelIcon level={h.level} size={12} /></span>{LEVEL_LABEL[h.level]}</span></td>
              <td className="num">{h.wbgt_c.toFixed(1)}°</td>
              <td>{workRest(h.work_min)}</td>
              <td className="num">{h.air_c.toFixed(0)}°</td>
              <td className="num">{h.rh_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Compact 24-cell risk strip for one day (used in the outlook). */
export function RiskStrip({ hours }: { hours: Hour[] }) {
  return (
    <div className="strip" role="img" aria-label="Risk level for each hour of the day, midnight to midnight">
      {hours.map((h) => (
        <span key={h.time} className={`strip-cell lv-fill-${h.level}`} title={`${clock(h.time)} ${LEVEL_LABEL[h.level]}, ${h.wbgt_c.toFixed(1)}°`} />
      ))}
    </div>
  )
}
