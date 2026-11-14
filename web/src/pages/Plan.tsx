import { useMemo, useState } from 'react'
import type { Prefs } from '../App'
import { api } from '../api'
import { Controls } from '../components/Controls'
import { Card, ErrorBox, Loading, RiskBadge } from '../components/ui'
import { clock, dayName, endClock, hourLabel, useLoad } from '../lib'

function localDates(n: number): string[] {
  // Days in Indian time; the API answers for the place's own timezone.
  const out: string[] = []
  const base = new Date(Date.now() + 5.5 * 3600000)
  for (let i = 0; i < n; i++) out.push(new Date(base.getTime() + i * 86400000).toISOString().slice(0, 10))
  return out
}

export function PlanPage({ prefs }: { prefs: Prefs }) {
  const dates = useMemo(() => localDates(7), [])
  // Late in the evening, most people are planning tomorrow.
  const [day, setDay] = useState(() => (new Date(Date.now() + 5.5 * 3600000).getUTCHours() >= 18 ? dates[1] : dates[0]))
  const [duration, setDuration] = useState(3)
  const [earliest, setEarliest] = useState(6)
  const [latest, setLatest] = useState(20)
  const { place, workload, acclimatised } = prefs
  const tooLong = latest - earliest < duration
  const [load, retry] = useLoad(
    () =>
      tooLong
        ? Promise.resolve(null)
        : api.plan({ lat: place.lat, lon: place.lon, workload, acclimatised, duration_hours: duration, day, earliest_hour: earliest, latest_hour: latest }),
    [place.lat, place.lon, workload, acclimatised, duration, day, earliest, latest],
  )

  return (
    <div className="page">
      <div className="page-head">
        <h1>Plan a job</h1>
        <p className="lede">Tell us how long the job takes and we find the safest time of day to do it.</p>
      </div>
      <Controls prefs={prefs} />
      <div className="controls">
        <div>
          <label className="field-label" htmlFor="plan-day">Day</label>
          <select id="plan-day" value={day} onChange={(e) => setDay(e.target.value)}>
            {dates.map((d) => <option key={d} value={d}>{dayName(d, dates[0])}</option>)}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="plan-dur">Job length</label>
          <select id="plan-dur" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => <option key={h} value={h}>{h} hour{h > 1 ? 's' : ''}</option>)}
          </select>
        </div>
        <div>
          <span className="field-label">Between</span>
          <div className="pair">
            <select aria-label="Earliest start" value={earliest} onChange={(e) => setEarliest(Number(e.target.value))}>
              {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{hourLabel(h)}</option>)}
            </select>
            <span>and</span>
            <select aria-label="Latest finish" value={latest} onChange={(e) => setLatest(Number(e.target.value))}>
              {Array.from({ length: 24 }, (_, h) => h + 1).map((h) => <option key={h} value={h}>{h === 24 ? 'midnight' : hourLabel(h)}</option>)}
            </select>
          </div>
        </div>
      </div>

      {tooLong && <ErrorBox message="The job is longer than the time you allowed. Widen the hours or shorten the job." />}
      {!tooLong && load.state === 'loading' && <Loading what="the best times" />}
      {!tooLong && load.state === 'error' && <ErrorBox message={load.message} retry={retry} />}
      {!tooLong && load.state === 'ready' && load.data && (
        <Card title={`Best times on ${dayName(day, dates[0]).toLowerCase() === 'today' ? 'today' : dayName(day, dates[0])}`}>
          {load.data.windows.length === 0 ? (
            <p>No time left in that window today. Try a later day or wider hours.</p>
          ) : (
            <ol className="windows">
              {load.data.windows.map((w, i) => {
                const effective = Math.round((w.work_min / 60) * 10) / 10
                return (
                  <li key={w.start} className={i === 0 ? 'best' : ''}>
                    <div className="win-time">
                      {i === 0 && <span className="eyebrow">Best choice</span>}
                      <strong>{clock(w.start)} to {endClock(w.end)}</strong>
                    </div>
                    <RiskBadge level={w.level} />
                    <p>
                      {w.work_min >= w.total_min
                        ? 'You can work straight through, with normal short breaks.'
                        : `With the rest breaks needed you get about ${effective} hours of work done in this ${w.total_min / 60}-hour slot.`}{' '}
                      Peak heat stress {w.peak_wbgt_c.toFixed(1)}°.
                    </p>
                  </li>
                )
              })}
            </ol>
          )}
        </Card>
      )}
    </div>
  )
}
