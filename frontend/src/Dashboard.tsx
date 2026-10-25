import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { api, ApiError } from './api'
import type { Session, Vehicle, VehicleInput } from './api'
import { CarArt, Modal, Notice } from './ui'

const money = (value: string) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const message = (error: unknown) => error instanceof Error ? error.message : 'Please try again.'
const unique = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b))
type Filters = { brands: string[]; models: string[]; categories: string[]; min: string; max: string; condition: string }
const emptyFilters: Filters = { brands: [], models: [], categories: [], min: '', max: '', condition: '' }
type Alerts = { threshold: number; vehicles: Vehicle[] }
type Action = { kind: 'purchase' | 'delete' | 'stock' | 'price' | 'edit'; vehicle: Vehicle }

function MultiSelect({ title, options, selected, change }: { title: string; options: string[]; selected: string[]; change: (values: string[]) => void }) {
  const [search, setSearch] = useState('')
  return <details className="multi-select" open><summary>{title}<span>{selected.length || 'Any'}</span></summary>
    <label className="sr-only" htmlFor={`filter-${title}`}>Search {title.toLowerCase()} options</label>
    <input id={`filter-${title}`} type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder={`Find ${title.toLowerCase()}…`} />
    <div className="option-list" role="group" aria-label={`${title} options`}>
      {options.filter(option => option.toLowerCase().includes(search.toLowerCase())).map(option => <label key={option} className="check-option"><input type="checkbox" checked={selected.includes(option)} onChange={() => change(selected.includes(option) ? selected.filter(value => value !== option) : [...selected, option])} />{option}</label>)}
      {!options.some(option => option.toLowerCase().includes(search.toLowerCase())) && <small>No matching options.</small>}
    </div>
    {selected.length > 0 && <button className="text-button text-xs" type="button" onClick={() => change([])}>Clear {title.toLowerCase()}</button>}
  </details>
}

export default function Dashboard({ session, expire }: { session: Session; expire: () => void }) {
  const admin = session.role === 'admin'
  const [catalogue, setCatalogue] = useState<Vehicle[]>([])
  const [matches, setMatches] = useState<Vehicle[]>([])
  const [alerts, setAlerts] = useState<Alerts | null>(null)
  const [alertError, setAlertError] = useState('')
  const [stockFilter, setStockFilter] = useState('all')
  const [draft, setDraft] = useState(emptyFilters)
  const [filters, setFilters] = useState(emptyFilters)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const [sort, setSort] = useState('relevance')
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)
  const [action, setAction] = useState<Action | null>(null)
  const [creating, setCreating] = useState(false)
  const expireRef = useRef(expire); expireRef.current = expire

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setLoadError(''); setAlertError('')
    const options = { signal: controller.signal }
    const all = api<Vehicle[]>('/vehicles', session.token, options)
    const found = query ? api<Vehicle[]>(`/vehicles/search?${query}`, session.token, options) : all
    Promise.all([all, found]).then(([allRows, result]) => { setCatalogue(allRows); setMatches(result) }).catch(err => {
      if (controller.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) expireRef.current()
      else setLoadError(message(err))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    if (admin) {
      setAlerts(null)
      api<Alerts>('/vehicles/alerts', session.token, options).then(setAlerts).catch(err => {
        if (controller.signal.aborted) return
        if (err instanceof ApiError && err.status === 401) expireRef.current()
        else setAlertError(message(err))
      })
    }
    return () => controller.abort()
  }, [session.token, admin, query, revision])

  function apply(value = search) {
    setError(''); setSuccess(''); setSuggestionsOpen(false)
    if (draft.min && draft.max && Number(draft.min) > Number(draft.max)) { setError('Minimum price cannot exceed maximum price.'); return }
    const params = new URLSearchParams()
    if (value.trim()) params.set('q', value.trim())
    if (draft.min) params.set('min_price', draft.min)
    if (draft.max) params.set('max_price', draft.max)
    setFilters(draft); setQuery(params.toString()); setRevision(value => value + 1)
  }
  function reset() { setDraft(emptyFilters); setFilters(emptyFilters); setSearch(''); setQuery(''); setStockFilter('all'); setSort('relevance'); setError(''); setSuccess(''); setSuggestionsOpen(false); setRevision(value => value + 1) }
  async function mutate(path: string, method: string, body?: unknown) {
    try { return await api<Vehicle>(path, session.token, { method, ...(body ? { body: JSON.stringify(body) } : {}) }) }
    catch (err) { if (err instanceof ApiError && err.status === 401) expireRef.current(); throw err }
  }
  function refreshed(text: string) { setSuccess(text); setError(''); setAction(null); setCreating(false); setRevision(value => value + 1) }
  async function saveVehicle(data: VehicleInput) {
    if (!action) { await mutate('/vehicles', 'POST', data); refreshed('Vehicle created.'); return }
    // PUT requires a full listing. Preserve the freshest stock we can read rather
    // than writing the editor's old quantity. API has no PATCH/version precondition.
    let current: Vehicle | undefined
    try { current = (await api<Vehicle[]>('/vehicles', session.token)).find(row => row.id === action.vehicle.id) }
    catch (err) { if (err instanceof ApiError && err.status === 401) expireRef.current(); throw err }
    if (!current) throw new Error('This vehicle no longer exists. Close this dialog and refresh.')
    const { id: _id, ...latest } = current
    await mutate(`/vehicles/${current.id}`, 'PUT', action.kind === 'price' ? { ...latest, price: data.price } : { ...data, quantity: current.quantity })
    refreshed('Vehicle saved.')
  }
  async function confirm() {
    if (!action) return
    setBusy(true); setError('')
    try {
      await mutate(`/vehicles/${action.vehicle.id}${action.kind === 'purchase' ? '/purchase' : ''}`, action.kind === 'purchase' ? 'POST' : 'DELETE')
      refreshed(action.kind === 'purchase' ? 'Purchase successful. One vehicle purchased.' : 'Vehicle deleted.')
    } catch (err) { setError(message(err)); setAction(null); setRevision(value => value + 1) }
    finally { setBusy(false) }
  }

  const modelOptions = unique(catalogue.filter(row => !draft.brands.length || draft.brands.includes(row.make)).map(row => row.model))
  const suggestions = unique(catalogue.flatMap(row => [row.make, `${row.make} ${row.model}`])).filter(value => value.toLowerCase().includes(search.trim().toLowerCase())).slice(0, 6)
  const maximum = Math.max(1, ...catalogue.map(row => Number(row.price)), Number(draft.max || 0), Number(draft.min || 0))
  const minSlider = Math.min(Number(draft.min || 0), maximum)
  const maxSlider = draft.max ? Number(draft.max) : maximum
  const alertIds = new Set(alerts?.vehicles.map(row => row.id))
  const vehicles = matches.filter(row =>
    (!filters.brands.length || filters.brands.includes(row.make)) &&
    (!filters.models.length || filters.models.includes(row.model)) &&
    (!filters.categories.length || filters.categories.includes(row.category)) &&
    (!filters.condition || row.condition === filters.condition) &&
    (stockFilter === 'all' || (stockFilter === 'out' ? row.quantity === 0 && alertIds.has(row.id) : alertIds.has(row.id))))
  if (sort !== 'relevance') vehicles.sort((a, b) => (sort === 'price-asc' ? Number(a.price) - Number(b.price) : sort === 'price-desc' ? Number(b.price) - Number(a.price) : sort === 'year' ? (b.year || 0) - (a.year || 0) : `${a.make} ${a.model}`.localeCompare(`${b.make} ${b.model}`)) || a.id - b.id)

  return <main id="main" className="dashboard">
    <section className="page-heading"><div><div className="eyebrow">{admin ? 'MOTORHAUS / ADMIN WORKSPACE' : 'THE MOTORHAUS COLLECTION'}</div><h1>{admin ? 'Inventory, in control' : 'Find your next drive'}<span>.</span></h1><p className="muted">{admin ? 'Manage listings, pricing and stock in one place.' : 'Explore the inventory. Find a vehicle that moves you.'}</p></div>{admin && <button className="primary" onClick={() => setCreating(true)}>+ Add vehicle</button>}</section>
    {admin && <section className="inventory-alerts" aria-label="Stock alerts">
      {alertError ? <Notice error>Stock alerts unavailable: {alertError} <button className="inline-link" onClick={() => setRevision(value => value + 1)}>Retry alerts</button></Notice> : !alerts ? <p role="status">Loading stock alerts…</p> : <>
        <div><h2>Stock watch</h2><small>Low stock: {alerts.threshold} units or fewer, including zero.</small></div>
        <div className="alert-actions"><button aria-pressed={stockFilter === 'all'} onClick={() => setStockFilter('all')}>All inventory</button><button aria-pressed={stockFilter === 'low'} onClick={() => setStockFilter('low')}>Low stock ({alerts.vehicles.length})</button><button aria-pressed={stockFilter === 'out'} onClick={() => setStockFilter('out')}>Out of stock ({alerts.vehicles.filter(row => row.quantity === 0).length})</button></div>
      </>}
    </section>}
    <form className="catalogue-search" onSubmit={event => { event.preventDefault(); apply() }}><div className="relative flex-1"><label htmlFor="catalogue-search" className="sr-only">Search inventory</label><input id="catalogue-search" type="search" maxLength={200} autoComplete="off" placeholder="Search a brand or model…" value={search} onChange={event => { setSearch(event.target.value); setSuggestionsOpen(true) }} onKeyDown={event => { if (event.key === 'Escape') setSuggestionsOpen(false) }} />
      {suggestionsOpen && search.trim() && suggestions.length > 0 && <ul className="search-suggestions" aria-label="Search suggestions">{suggestions.map(value => <li key={value}><button type="button" onClick={() => { setSearch(value); apply(value) }}>{value}<span>↗</span></button></li>)}</ul>}
    </div><button className="primary" type="submit">Search</button></form>
    <div className="inventory-layout"><aside className="filter-panel"><h2 className="mb-5">Find your fit</h2><form onSubmit={event => { event.preventDefault(); apply() }}><fieldset disabled={busy} className="space-y-4">
      <MultiSelect title="Brand" options={unique(catalogue.map(row => row.make))} selected={draft.brands} change={brands => { const models = unique(catalogue.filter(row => !brands.length || brands.includes(row.make)).map(row => row.model)); setDraft({ ...draft, brands, models: draft.models.filter(model => models.includes(model)) }) }} />
      <MultiSelect title="Model" options={modelOptions} selected={draft.models} change={models => setDraft({ ...draft, models })} />
      <MultiSelect title="Category" options={unique(catalogue.map(row => row.category))} selected={draft.categories} change={categories => setDraft({ ...draft, categories })} />
      <label>Condition<select value={draft.condition} onChange={event => setDraft({ ...draft, condition: event.target.value })}><option value="">Any condition</option><option value="new">New</option><option value="used">Used</option></select></label>
      <fieldset className="price-filter"><legend>Price range</legend><div className="dual-range" style={{ '--range-start': `${minSlider / maximum * 100}%`, '--range-end': `${maxSlider / maximum * 100}%` } as CSSProperties}>
        <input type="range" aria-label="Minimum price slider" min="0" max={maximum} step="0.01" value={minSlider} onChange={event => setDraft({ ...draft, min: String(Math.min(Number(event.target.value), maxSlider)) })} />
        <input type="range" aria-label="Maximum price slider" min="0" max={maximum} step="0.01" value={maxSlider} onChange={event => setDraft({ ...draft, max: String(Math.max(Number(event.target.value), minSlider)) })} />
      </div><div className="grid grid-cols-2 gap-3"><label>Min price<input type="number" min="0" max="9999999999.99" step="0.01" placeholder="Any" value={draft.min} onChange={event => setDraft({ ...draft, min: event.target.value })} /></label><label>Max price<input type="number" min="0" max="9999999999.99" step="0.01" placeholder="Any" value={draft.max} onChange={event => setDraft({ ...draft, max: event.target.value })} /></label></div></fieldset>
      <button className="primary w-full" type="submit">Apply filters</button><button type="button" className="text-button w-full" onClick={reset}>Clear filters</button>
    </fieldset></form></aside>
    <section className="min-w-0" aria-label="Vehicle inventory"><div className="results-heading"><h2>{admin ? 'Vehicle inventory' : 'Available collection'} <span className="muted text-sm font-normal">({loading ? '…' : vehicles.length})</span></h2><label className="sort-label">Sort by<select value={sort} onChange={event => setSort(event.target.value)}><option value="relevance">Best match</option><option value="price-asc">Price: low to high</option><option value="price-desc">Price: high to low</option><option value="year">Newest year</option><option value="name">Brand & model</option></select></label></div>
      {error && <Notice error>{error}</Notice>}{loadError && <Notice error>{loadError} <button className="inline-link" onClick={() => setRevision(value => value + 1)}>Refresh inventory</button></Notice>}{success && <Notice>{success}</Notice>}
      {loading ? <div role="status" className="empty-state">Loading the collection…</div> : loadError ? <div className="empty-state">Inventory could not be loaded. Please refresh to continue.</div> : !vehicles.length ? <div className="empty-state"><CarArt /><h3>No matching vehicles</h3><p>Try a different search or clear your filters.</p><button className="text-button" onClick={reset}>Reset search</button></div> : admin ? <div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th>Vehicle</th><th>Price</th><th>Stock</th><th>Manage</th></tr></thead><tbody>{vehicles.map(vehicle => <tr key={vehicle.id} aria-label={`${vehicle.make} ${vehicle.model}`}>
        <td><strong>{vehicle.make} {vehicle.model}</strong><small>{vehicle.year || 'Year unspecified'} · {vehicle.category} · {vehicle.condition === 'new' ? 'New' : 'Used'} · ID {vehicle.id}</small></td>
        <td><span>{money(vehicle.price)}</span><button className="row-link" onClick={() => setAction({ kind: 'price', vehicle })}>Edit price</button></td>
        <td><span className={vehicle.quantity ? 'stock' : 'stock out'}>{vehicle.quantity ? `${vehicle.quantity} in stock` : 'Out of stock'}</span>{alerts && alertIds.has(vehicle.id) && vehicle.quantity > 0 && <small className="low-stock-label">Low stock</small>}<button className="row-link" onClick={() => setAction({ kind: 'stock', vehicle })}>Adjust stock</button></td>
        <td><div className="row-actions"><button className="text-button" onClick={() => setAction({ kind: 'edit', vehicle })}>Edit vehicle</button><button className="danger-link" onClick={() => setAction({ kind: 'delete', vehicle })}>Delete</button></div></td>
      </tr>)}</tbody></table></div> : <div className="vehicle-grid">{vehicles.map(vehicle => <article key={vehicle.id} className="vehicle-card" aria-label={`${vehicle.make} ${vehicle.model}`}><div className="vehicle-visual"><span className="category-tag">{vehicle.category} · {vehicle.condition === 'new' ? 'New' : 'Used'}</span><CarArt /><span className="illustration-label">VEHICLE ILLUSTRATION</span></div><div className="card-body"><div className="flex justify-between gap-2"><span className="vehicle-year">{vehicle.year || 'Year not specified'}</span><span className={vehicle.quantity ? 'stock' : 'stock out'}>{vehicle.quantity ? `${vehicle.quantity} in stock` : 'Out of stock'}</span></div><h3>{vehicle.make} {vehicle.model}</h3><div className="price-row"><strong>{money(vehicle.price)}</strong><span>Price · ID {vehicle.id}</span></div><button className="primary w-full" disabled={!vehicle.quantity || busy} onClick={() => setAction({ kind: 'purchase', vehicle })}>{vehicle.quantity ? 'Purchase vehicle ↗' : 'Currently unavailable'}</button></div></article>)}</div>}
    </section></div>
    {(creating || action?.kind === 'edit' || action?.kind === 'price') && <VehicleEditor vehicle={action?.vehicle || null} priceOnly={action?.kind === 'price'} save={saveVehicle} close={() => { setCreating(false); setAction(null) }} />}
    {action?.kind === 'stock' && <StockEditor vehicle={action.vehicle} close={() => setAction(null)} save={async delta => { await mutate(`/vehicles/${action.vehicle.id}/adjust-stock`, 'POST', { delta }); refreshed('Stock adjusted.') }} />}
    {(action?.kind === 'purchase' || action?.kind === 'delete') && <Modal title={action.kind === 'delete' ? 'Delete this vehicle?' : 'Confirm your purchase'} close={() => { if (!busy) setAction(null) }} busy={busy}><p className="muted mb-6">{action.vehicle.make} {action.vehicle.model}{action.kind === 'delete' ? ' will be permanently removed.' : ` · One unit at ${money(action.vehicle.price)}.`}</p><div className="flex justify-end gap-3"><button className="secondary" disabled={busy} onClick={() => setAction(null)}>Cancel</button><button className={action.kind === 'delete' ? 'danger' : 'primary'} disabled={busy} onClick={confirm}>{busy ? 'Processing…' : action.kind === 'delete' ? 'Confirm delete' : 'Confirm purchase'}</button></div></Modal>}
  </main>
}

function VehicleEditor({ vehicle, priceOnly, save, close }: { vehicle: Vehicle | null; priceOnly?: boolean; save: (data: VehicleInput) => Promise<void>; close: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const data = new FormData(event.currentTarget)
    const payload: VehicleInput = priceOnly && vehicle ? { ...vehicle, price: String(data.get('price')) } : {
      make: String(data.get('make')).trim(), model: String(data.get('model')).trim(), category: String(data.get('category')).trim(),
      year: data.get('year') ? Number(data.get('year')) : null, price: String(data.get('price')),
      condition: data.get('condition') as 'new' | 'used', quantity: vehicle?.quantity ?? Number(data.get('quantity')),
    }
    try { await save(payload) } catch (err) { setError(message(err)); setBusy(false) }
  }
  return <Modal title={priceOnly ? 'Edit price' : vehicle ? 'Edit vehicle' : 'Add a vehicle'} close={close} busy={busy}>{error && <Notice error>{error}</Notice>}<form onSubmit={submit}><fieldset disabled={busy} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
    {!priceOnly && <>{(['make', 'model', 'category'] as const).map(key => <label key={key}>{key[0].toUpperCase() + key.slice(1)}<input name={key} required maxLength={key === 'category' ? 50 : 100} defaultValue={vehicle?.[key]} /></label>)}
    <label>Year (optional)<input name="year" type="number" min="1886" max={new Date().getUTCFullYear() + 1} step="1" defaultValue={vehicle?.year || ''} /></label><label>Condition<select name="condition" defaultValue={vehicle?.condition || 'used'}><option value="new">New</option><option value="used">Used</option></select></label></>}
    <label>Price<input name="price" type="number" min="0.01" max="9999999999.99" step="0.01" required defaultValue={vehicle?.price} /></label>
    {!vehicle && <label>Quantity in stock<input name="quantity" type="number" min="0" max="2147483647" step="1" required defaultValue={0} /></label>}
    {vehicle && !priceOnly && <small>Use Adjust stock to increase or decrease inventory.</small>}
    <div className="flex justify-end gap-3 sm:col-span-2 mt-3"><button className="secondary" type="button" onClick={close}>Cancel</button><button className="primary" type="submit">{busy ? 'Saving…' : 'Save vehicle'}</button></div>
  </fieldset></form></Modal>
}

function StockEditor({ vehicle, save, close }: { vehicle: Vehicle; save: (delta: number) => Promise<void>; close: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try { await save(Number(data.get('amount')) * (data.get('direction') === 'decrease' ? -1 : 1)) }
    catch (err) { setError(message(err)); setBusy(false) }
  }
  return <Modal title="Adjust stock" close={close} busy={busy}><p className="muted mb-4">{vehicle.make} {vehicle.model} · Last loaded quantity: {vehicle.quantity}</p>{error && <Notice error>{error}</Notice>}<form onSubmit={submit}><fieldset disabled={busy} className="space-y-4"><label>Operation<select name="direction"><option value="increase">Increase stock</option><option value="decrease">Decrease stock</option></select></label><label>Units<input name="amount" type="number" required min="1" max="2147483647" step="1" defaultValue={1} /></label><button className="primary w-full" type="submit">{busy ? 'Updating…' : 'Apply adjustment'}</button></fieldset></form></Modal>
}
