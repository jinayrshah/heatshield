import { useEffect, useState } from 'react'
import type { Prefs } from '../App'
import { ApiError, api, type AlertItem, type Place, type User, type Workload } from '../api'
import { WorkloadSelect } from '../components/Controls'
import { LocationPicker } from '../components/LocationPicker'
import { Card, ErrorBox, Loading, RiskBadge, Toggle } from '../components/ui'
import { ago, hourLabel, useStored } from '../lib'

export function AlertsPage({ prefs }: { prefs: Prefs }) {
  const [token, setToken] = useStored<string | null>('hs.token', null)
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.me(token).then(setUser, (e: ApiError) => {
      if (e.status === 401) setToken(null)
      else setError(e.message)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return (
    <div className="page">
      <div className="page-head">
        <h1>My heat alerts</h1>
        <p className="lede">A morning message with today's dangerous hours and your work and rest times, plus a reminder when it turns dangerous during your shift.</p>
      </div>
      {!token && <SignUp prefs={prefs} onDone={(t, u) => { setToken(t); setUser(u) }} />}
      {token && !user && !error && <Loading what="your account" />}
      {token && error && <ErrorBox message={error} />}
      {token && user && (
        <Account
          token={token}
          user={user}
          setUser={setUser}
          onDeleted={() => {
            setToken(null)
            setUser(null)
          }}
        />
      )}
    </div>
  )
}

function HoursPicker({ start, end, onChange }: { start: number; end: number; onChange: (s: number, e: number) => void }) {
  return (
    <div>
      <span className="field-label">Usual working hours</span>
      <div className="pair">
        <select aria-label="Start" value={start} onChange={(e) => onChange(Number(e.target.value), end)}>
          {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{hourLabel(h)}</option>)}
        </select>
        <span>to</span>
        <select aria-label="End" value={end} onChange={(e) => onChange(start, Number(e.target.value))}>
          {Array.from({ length: 24 }, (_, h) => h + 1).map((h) => <option key={h} value={h}>{h === 24 ? 'midnight' : hourLabel(h)}</option>)}
        </select>
      </div>
      <p className="hint">Reminders are only sent inside these hours.</p>
    </div>
  )
}

function SignUp({ prefs, onDone }: { prefs: Prefs; onDone: (token: string, user: User) => void }) {
  const [place, setPlace] = useState<Place>(prefs.place)
  const [name, setName] = useState('')
  const [start, setStart] = useState(8)
  const [end, setEnd] = useState(18)
  const [newToHeat, setNewToHeat] = useState(!prefs.acclimatised)
  const [whatsapp, setWhatsapp] = useState('')
  const [agree, setAgree] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (end <= start) return setError('Work must end after it starts.')
    setBusy(true)
    setError('')
    try {
      const r = await api.signUp({
        lat: place.lat,
        lon: place.lon,
        area_label: place.label === 'My location' ? '' : place.label,
        name,
        workload: prefs.workload as Workload,
        work_start: start,
        work_end: end,
        new_to_heat: newToHeat,
        whatsapp_number: whatsapp,
      })
      onDone(r.token, r.user)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="Sign up for free alerts">
      <form className="form" onSubmit={submit}>
        <div>
          <label className="field-label" htmlFor="name">Your name (optional)</label>
          <input id="name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoComplete="given-name" />
        </div>
        <LocationPicker value={place} onChange={setPlace} />
        <WorkloadSelect prefs={prefs} />
        <HoursPicker start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e) }} />
        <Toggle checked={newToHeat} onChange={setNewToHeat} label="I am new to working in the heat" hint="Stricter limits for the next 14 days while your body adjusts." />
        {prefs.meta?.channels.whatsapp && (
          <div>
            <label className="field-label" htmlFor="wa">WhatsApp number (optional)</label>
            <input id="wa" inputMode="tel" placeholder="+91 98123 45678" value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} autoComplete="tel" />
          </div>
        )}
        <label className="check">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} required />
          <span>
            I understand this is guidance, not medical advice. HeatShield stores my area (to about 1 km, never my exact location), work type and hours to send alerts, and I can delete everything at any time.
          </span>
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn-primary btn-big" disabled={busy || !agree}>{busy ? 'Signing up…' : 'Start my alerts'}</button>
        <p className="hint">Your account lives on this device. No password or phone number needed.</p>
      </form>
    </Card>
  )
}

function Account({ token, user, setUser, onDeleted }: { token: string; user: User; setUser: (u: User) => void; onDeleted: () => void }) {
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [whatsapp, setWhatsapp] = useState(user.whatsapp.number)

  const loadAlerts = () => api.myAlerts(token).then((r) => setAlerts(r.alerts), (e: Error) => setError(e.message))
  useEffect(() => {
    loadAlerts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const patch = async (body: Record<string, unknown>, label = 'save') => {
    setBusy(label)
    setError('')
    try {
      setUser(await api.updateMe(token, body))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy('')
    }
  }

  const preview = async () => {
    setBusy('preview')
    setError('')
    try {
      await api.previewAlert(token)
      await loadAlerts()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy('')
    }
  }

  const remove = async () => {
    setBusy('delete')
    try {
      await api.deleteMe(token)
      onDeleted()
    } catch (e) {
      setError((e as Error).message)
      setBusy('')
    }
  }

  const fakePrefs = {
    workload: user.workload,
    setWorkload: (w: Workload) => patch({ workload: w }),
    meta: null,
  } as unknown as Prefs

  return (
    <>
      <Card className={user.paused ? 'paused' : ''} title={user.name ? `Hello ${user.name}` : 'Your alerts'} aside={<span className={`pill ${user.paused ? 'pill-off' : 'pill-on'}`}>{user.paused ? 'Paused' : 'On'}</span>}>
        <p>
          Alerts for <strong>{user.area_label}</strong>. Morning alert from 06:00, reminders between {hourLabel(user.work_start)} and {user.work_end === 24 ? 'midnight' : hourLabel(user.work_end)}.
          {user.new_to_heat && user.new_to_heat_until && ` Stricter "new to the heat" limits until ${user.new_to_heat_until}.`}
        </p>
        <div className="btn-row">
          <button className="btn btn-primary" onClick={preview} disabled={!!busy}>{busy === 'preview' ? 'Sending…' : "Send me today's alert now"}</button>
          <button className="btn" onClick={() => patch({ paused: !user.paused }, 'pause')} disabled={!!busy}>{user.paused ? 'Resume alerts' : 'Pause alerts'}</button>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
      </Card>

      <Card title="Where alerts go">
        <ul className="channels">
          <li>
            <strong>This website</strong>
            <span className="pill pill-on">On</span>
            <span className="hint">Alerts appear in the inbox below.</span>
          </li>
          <li>
            <strong>Telegram</strong>
            {user.telegram.connected ? (
              <span className="pill pill-on">Connected</span>
            ) : user.telegram.link ? (
              <a className="btn" href={user.telegram.link} target="_blank" rel="noreferrer">Connect Telegram</a>
            ) : (
              <span className="pill pill-off">Not set up on this server</span>
            )}
            <span className="hint">{user.telegram.connected ? 'Alerts also go to your Telegram chat.' : 'Opens the HeatShield bot. Press Start to link it to this account.'}</span>
          </li>
          <li>
            <strong>WhatsApp</strong>
            {user.whatsapp.available ? (
              <form className="inline-form" onSubmit={(e) => { e.preventDefault(); patch({ whatsapp_number: whatsapp }, 'wa') }}>
                <input aria-label="WhatsApp number" inputMode="tel" placeholder="+91 98123 45678" value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
                <button className="btn" disabled={busy === 'wa'}>Save</button>
              </form>
            ) : (
              <span className="pill pill-off">Not set up on this server</span>
            )}
            <span className="hint">{user.whatsapp.number ? `Sending to ${user.whatsapp.number}.` : 'Add your number with country code.'}</span>
          </li>
        </ul>
      </Card>

      <Card title="Inbox" aside={<button className="btn btn-quiet" onClick={loadAlerts}>Refresh</button>}>
        {alerts === null && <Loading what="alerts" />}
        {alerts?.length === 0 && <p className="muted">No alerts yet. Your first one arrives at 06:00, or press "Send me today's alert now".</p>}
        <ul className="inbox">
          {alerts?.map((a) => (
            <li key={a.id}>
              <details>
                <summary>
                  <RiskBadge level={a.level} />
                  <span className="inbox-title">{a.title}</span>
                  <span className="muted">{ago(a.created_at)}</span>
                </summary>
                <pre className="alert-body">{a.body}</pre>
                <p className="hint">
                  {Object.entries(a.deliveries).map(([ch, st]) => `${ch}: ${st}`).join(' · ') || 'Not delivered on any channel'}
                </p>
              </details>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Settings">
        <div className="form">
          <LocationPicker value={{ label: user.area_label, lat: user.lat, lon: user.lon }} onChange={(p) => patch({ lat: p.lat, lon: p.lon, area_label: p.label === 'My location' ? '' : p.label }, 'place')} />
          <WorkloadSelect prefs={fakePrefs} />
          <HoursPicker start={user.work_start} end={user.work_end} onChange={(s, e) => (e > s ? patch({ work_start: s, work_end: e }) : setError('Work must end after it starts.'))} />
          <Toggle checked={user.new_to_heat} onChange={(v) => patch({ new_to_heat: v })} label="New to working in the heat" hint="Stricter limits for 14 days." />
          <Toggle checked={user.morning_alerts} onChange={(v) => patch({ morning_alerts: v })} label="Morning alert at 06:00" />
          <Toggle checked={user.peak_reminders} onChange={(v) => patch({ peak_reminders: v })} label="Reminder when it turns dangerous during work" />
          <Toggle checked={user.warm_night_alerts} onChange={(v) => patch({ warm_night_alerts: v })} label="Warm-night alert in the evening" />
        </div>
      </Card>

      <Card title="Delete my data">
        <p>This removes your account, settings and every alert stored for you. It cannot be undone.</p>
        {confirmDelete ? (
          <div className="btn-row">
            <button className="btn btn-danger" onClick={remove} disabled={busy === 'delete'}>Yes, delete everything</button>
            <button className="btn" onClick={() => setConfirmDelete(false)}>Cancel</button>
          </div>
        ) : (
          <button className="btn" onClick={() => setConfirmDelete(true)}>Delete my data</button>
        )}
      </Card>
    </>
  )
}
