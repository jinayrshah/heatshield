import type { ReactNode } from 'react'
import type { Level } from '../api'
import { LEVEL_LABEL } from '../lib'

/** Each level has its own shape, so risk never depends on colour alone. */
export function LevelIcon({ level, size = 18 }: { level: Level; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 20 20', 'aria-hidden': true } as const
  const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 2.2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const
  if (level === 'safe')
    return (
      <svg {...common}><circle cx="10" cy="10" r="8" {...stroke} /><path d="m6.500 10.200 2.400 2.400 4.600-5" {...stroke} /></svg>
    )
  if (level === 'caution')
    return (
      <svg {...common}><path d="M10 2.800 18 16.500H2z" {...stroke} /><path d="M10 8v3.600M10 14v.100" {...stroke} /></svg>
    )
  if (level === 'high')
    return (
      <svg {...common}><path d="M10 1.800 18.200 10 10 18.200 1.800 10z" {...stroke} /><path d="M10 6.200v4.600M10 13.400v.100" {...stroke} /></svg>
    )
  return (
    <svg {...common}><path d="M6.600 2h6.800L18 6.600v6.800L13.400 18H6.600L2 13.400V6.600z" {...stroke} /><path d="m7.200 7.200 5.600 5.600M12.800 7.200l-5.600 5.600" {...stroke} /></svg>
  )
}

export function RiskBadge({ level, big = false }: { level: Level; big?: boolean }) {
  return (
    <span className={`badge lv-${level}${big ? ' badge-big' : ''}`}>
      <LevelIcon level={level} size={big ? 26 : 16} />
      {LEVEL_LABEL[level]}
    </span>
  )
}

export function Card({ title, aside, children, className = '' }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || aside) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {aside}
        </header>
      )}
      {children}
    </section>
  )
}

export function Loading({ what = 'the forecast' }: { what?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" />
      Loading {what}…
    </div>
  )
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      {retry && (
        <button className="btn" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function Toggle({ checked, onChange, label, hint, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string; disabled?: boolean }) {
  return (
    <label className="toggle">
      <input type="checkbox" role="switch" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" aria-hidden="true" />
      <span className="toggle-text">
        {label}
        {hint && <small>{hint}</small>}
      </span>
    </label>
  )
}

export function Legend() {
  return (
    <ul className="legend" aria-label="Risk levels">
      {(['safe', 'caution', 'high', 'extreme'] as Level[]).map((l) => (
        <li key={l}>
          <span className={`swatch lv-${l}`}><LevelIcon level={l} size={12} /></span>
          {LEVEL_LABEL[l]}
        </li>
      ))}
    </ul>
  )
}
