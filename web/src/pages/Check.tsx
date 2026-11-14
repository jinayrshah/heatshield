import { useState } from 'react'
import type { Prefs } from '../App'
import { api, type Day, type Forecast, type Hour } from '../api'
import { Controls } from '../components/Controls'
import { HourChart, HourTable, RiskStrip } from '../components/HourChart'
import { Card, ErrorBox, Legend, LevelIcon, Loading, RiskBadge } from '../components/ui'
import { ago, clock, dayName, dayOf, LEVEL_LABEL, rangeText, useLoad, workRest } from '../lib'

export function CheckPage({ prefs }: { prefs: Prefs }) {
  const { place, workload, acclimatised } = prefs
  const [load, retry] = useLoad(() => api.forecast(place.lat, place.lon, workload, acclimatised), [place.lat, place.lon, workload, acclimatised])

  return (
    <div className="page">
      <div className="page-head">
        <h1>How hot is it for work?</h1>
        <p className="lede">Heat stress for outdoor work, hour by hour, with how long you can safely work in each hour.</p>
      </div>
      <Controls prefs={prefs} />
      {load.state === 'loading' && <Loading />}
      {load.state === 'error' && <ErrorBox message={load.message} retry={retry} />}
      {load.state === 'ready' && <ForecastView fc={load.data} placeLabel={place.label} />}
    </div>
  )
}

function ForecastView({ fc, placeLabel }: { fc: Forecast; placeLabel: string }) {
  const todayDate = fc.days[0]?.date
  const [selected, setSelected] = useState(todayDate)
  const [showTable, setShowTable] = useState(false)
  const day = fc.days.find((d) => d.date === selected) ?? fc.days[0]
  const hours = fc.hours.filter((h) => dayOf(h.time) === day.date)
  const byDay = (d: Day) => fc.hours.filter((h) => dayOf(h.time) === d.date)

  return (
    <>
      {fc.location.stale && (
        <div className="banner banner-warn" role="status">The latest forecast could not be fetched, so this is the previous one from {ago(fc.location.fetched_at)}.</div>
      )}
      <div className="grid-2">
        <NowCard now={fc.now} placeLabel={placeLabel} ward={fc.location.ward} />
        <DayCard day={fc.days[0]} title="Today" />
      </div>

      <Card
        title={`${dayName(day.date, todayDate)} hour by hour`}
        aside={
          <button className="btn btn-quiet" onClick={() => setShowTable(!showTable)} aria-pressed={showTable}>
            {showTable ? 'Show chart' : 'Show table'}
          </button>
        }
      >
        <div className="day-tabs" role="tablist" aria-label="Choose a day">
          {fc.days.map((d) => (
            <button key={d.date} role="tab" aria-selected={d.date === day.date} className={d.date === day.date ? 'on' : ''} onClick={() => setSelected(d.date)}>
              {dayName(d.date, todayDate, true)}
            </button>
          ))}
        </div>
        {showTable ? <HourTable hours={hours} /> : <HourChart hours={hours} nowTime={fc.now?.time} />}
        <Legend />
      </Card>

      <Card title="7-day outlook">
        <ul className="outlook">
          {fc.days.map((d) => (
            <li key={d.date}>
              <button className={`outlook-row${d.date === day.date ? ' on' : ''}`} onClick={() => setSelected(d.date)}>
                <span className="outlook-day">{dayName(d.date, todayDate)}</span>
                <RiskBadge level={d.level} />
                <span className="outlook-peak">Peak {d.peak_wbgt_c.toFixed(1)}° at {clock(d.peak_time)}</span>
                <RiskStrip hours={byDay(d)} />
                <span className="outlook-note">
                  {d.dangerous.length ? `Dangerous ${rangeText(d.dangerous)}` : d.caution.length ? `Caution ${rangeText(d.caution)}` : 'No risky hours'}
                  {d.warm_night && ' · Warm night'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Card>
      <p className="meta-line">
        Forecast for {fc.location.lat.toFixed(2)}, {fc.location.lon.toFixed(2)} ({fc.location.tz}), updated {ago(fc.location.fetched_at)}.
      </p>
    </>
  )
}

function NowCard({ now, placeLabel, ward }: { now: Hour | null; placeLabel: string; ward: string | null }) {
  if (!now) return <Card title="Right now"><p>No forecast for this hour yet.</p></Card>
  return (
    <Card className={`now lv-tint-${now.level}`}>
      <p className="eyebrow">Right now · {placeLabel}{ward && !placeLabel.includes(`${ward} ward`) ? ` · ${ward} ward` : ''}</p>
      <div className="now-main">
        <RiskBadge level={now.level} big />
        <div className="now-num">
          <span className="big-num">{now.wbgt_c.toFixed(1)}°</span>
          <span className="muted">heat stress (WBGT)</span>
        </div>
      </div>
      <p className="now-plan">
        <LevelIcon level={now.level} /> {workRest(now.work_min)}
      </p>
      <dl className="facts">
        <div><dt>Air</dt><dd>{now.air_c.toFixed(0)}°C</dd></div>
        <div><dt>Humidity</dt><dd>{now.rh_pct}%</dd></div>
        <div><dt>Sun</dt><dd>{now.solar_wm2} W/m²</dd></div>
        <div><dt>Limit</dt><dd>{now.limit_c.toFixed(1)}°</dd></div>
      </dl>
    </Card>
  )
}

export function DayCard({ day, title }: { day: Day; title: string }) {
  return (
    <Card title={title} aside={<RiskBadge level={day.level} />}>
      <ul className="daylist">
        <li>
          <strong>Peak</strong> {day.peak_wbgt_c.toFixed(1)}° at {clock(day.peak_time)}, air up to {day.max_air_c.toFixed(0)}°C
        </li>
        <li>
          <strong>{day.dangerous.length ? 'Dangerous hours' : 'Caution hours'}</strong>{' '}
          {day.dangerous.length ? rangeText(day.dangerous) : day.caution.length ? rangeText(day.caution) : 'none'}
        </li>
        <li><strong>What to do</strong> {day.advice}</li>
        <li><strong>Water</strong> {day.water}</li>
        {day.night_min_air_c !== null && (
          <li>
            <strong>Tonight</strong> lowest {day.night_min_air_c.toFixed(0)}°C
            {day.warm_night ? `. A warm night: the body recovers less, so tomorrow is riskier.` : ''}
          </li>
        )}
      </ul>
      <p className="sr-only">Overall risk {LEVEL_LABEL[day.level]}</p>
    </Card>
  )
}
