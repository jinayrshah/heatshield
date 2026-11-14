import type { Prefs } from '../App'
import type { Workload } from '../api'
import { LocationPicker } from './LocationPicker'

const FALLBACK: { id: Workload; label: string; examples: string }[] = [
  { id: 'light', label: 'Light', examples: 'vending, traffic duty, security, driving' },
  { id: 'moderate', label: 'Moderate', examples: 'delivery riding, cleaning, walking with a load' },
  { id: 'heavy', label: 'Heavy', examples: 'construction, carrying bricks, digging' },
  { id: 'very_heavy', label: 'Very heavy', examples: 'heavy shovelling, loading trucks' },
]

export function WorkloadSelect({ prefs }: { prefs: Prefs }) {
  const options = prefs.meta?.workloads ?? FALLBACK
  const current = options.find((o) => o.id === prefs.workload)
  return (
    <div>
      <label className="field-label" htmlFor="workload">Type of work</label>
      <select id="workload" value={prefs.workload} onChange={(e) => prefs.setWorkload(e.target.value as Workload)}>
        {options.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
      <p className="hint">{current ? `For example ${current.examples}.` : ''}</p>
    </div>
  )
}

export function Controls({ prefs, location = true }: { prefs: Prefs; location?: boolean }) {
  return (
    <div className="controls">
      {location && <LocationPicker value={prefs.place} onChange={prefs.setPlace} />}
      <WorkloadSelect prefs={prefs} />
      <div>
        <span className="field-label">Used to the heat?</span>
        <div className="seg" role="radiogroup" aria-label="Used to the heat?">
          <button role="radio" aria-checked={prefs.acclimatised} className={prefs.acclimatised ? 'on' : ''} onClick={() => prefs.setAcclimatised(true)}>Yes</button>
          <button role="radio" aria-checked={!prefs.acclimatised} className={!prefs.acclimatised ? 'on' : ''} onClick={() => prefs.setAcclimatised(false)}>New to it</button>
        </div>
        <p className="hint">Choose "New to it" for the first two weeks of hot work, or after a week or more away.</p>
      </div>
    </div>
  )
}
