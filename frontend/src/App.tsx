import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api, ApiError, readToken } from './api'
import type { Session, Vehicle, VehicleInput } from './api'

const money = (value: string) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.'
function savedSession() { try { return readToken(sessionStorage.getItem('dealership-token') || '') } catch { return null } }

function Brand() { return <a href="#/" className="brand" aria-label="Motorhaus home"><span className="brand-mark">M<span>↗</span></span><span>MOTORHAUS<small>THE DEALERSHIP COLLECTION</small></span></a> }
function CarArt({ large = false }: { large?: boolean }) {
  return <svg className={large ? 'car-art large' : 'car-art'} viewBox="0 0 440 180" fill="none" aria-hidden="true">
    <ellipse cx="224" cy="151" rx="174" ry="9" fill="currentColor" opacity=".08" />
    <path d="M48 120 64 92 120 80 166 40H273L324 81 376 95 394 120V139H48Z" fill="currentColor" opacity=".14" />
    <path d="m66 93 57-10 44-40h104l52 40 53 15 15 23v17H50v-17l16-28Z" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" />
    <path d="m145 81 30-29h40v29Zm82 0V52h38l35 29Z" fill="currentColor" opacity=".35" />
    <path d="M219 88v41m19-33h13M55 112h30m277-4h20" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    {[119, 323].map(x => <g key={x}><circle cx={x} cy="137" r="24" fill="#f5f4ee" stroke="currentColor" strokeWidth="5" /><circle cx={x} cy="137" r="11" fill="currentColor" opacity=".5" /></g>)}
  </svg>
}
function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={error ? 'notice error' : 'notice'} role={error ? 'alert' : 'status'}>{children}</div>
}

export default function App() {
  const [session, setSession] = useState<Session | null>(savedSession)
  const [notice, setNotice] = useState('')
  const [route, setRoute] = useState(location.hash)
  useEffect(() => { const change = () => setRoute(location.hash); addEventListener('hashchange', change); return () => removeEventListener('hashchange', change) }, [])
  const logout = useCallback((text = '') => {
    try { sessionStorage.removeItem('dealership-token') } catch { /* Memory-only fallback. */ }
    setSession(null); setNotice(text); location.hash = '/login'
  }, [])
  useEffect(() => {
    if (!session) return
    const timer = setTimeout(() => logout('Your session expired. Please sign in again.'), Math.max(0, session.expires - Date.now()))
    return () => clearTimeout(timer)
  }, [session, logout])
  function login(token: string) {
    const next = readToken(token)
    if (!next) throw new Error('The server returned an invalid session. Please sign in again.')
    try { sessionStorage.setItem('dealership-token', token) } catch { /* Continue in memory if storage is unavailable. */ }
    setSession(next); setNotice(''); location.hash = '/'
  }
  return <>
    <a href="#main" className="skip-link">Skip to content</a>
    <header className="site-header"><Brand />{session && <div className="flex items-center gap-4"><span className="role-badge">{session.role === 'admin' ? 'Admin workspace' : 'Customer account'}</span><button className="text-button" onClick={() => logout()}>Sign out ↗</button></div>}</header>
    {session ? <Dashboard session={session} expire={() => logout('Your session is no longer valid. Please sign in again.')} />
      : <Auth key={route} register={route === '#/register'} login={login} notice={notice} />}
    <footer className="site-footer"><span>Motorhaus · A better way to find your next drive.</span><span>Car Dealership Inventory System</span></footer>
  </>
}

function Auth({ register, login, notice }: { register: boolean; login: (token: string) => void; notice: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const data = new FormData(event.currentTarget)
    const credentials = { email: String(data.get('email')).trim(), password: String(data.get('password')) }
    let created = false
    try {
      if (register) { await api('/auth/register', undefined, { method: 'POST', body: JSON.stringify({ ...credentials, full_name: String(data.get('full_name')).trim() }) }); created = true }
      const result = await api<{ access_token: string }>('/auth/login', undefined, { method: 'POST', body: JSON.stringify(credentials) })
      login(result.access_token)
    } catch (err) { setError((created ? 'Account created. Sign in to continue. ' : '') + message(err)) }
    finally { setBusy(false) }
  }
  return <main id="main" className="auth-layout">
    <section className="auth-story"><div className="eyebrow">YOUR NEXT CHAPTER, ON FOUR WHEELS</div><h1>Good cars.<br />Great possibilities.</h1><p>Explore the collection, find your fit, and make your next move with confidence.</p><CarArt large /><div className="story-caption"><span>01 / THE COLLECTION</span><span>Find your next drive ↗</span></div></section>
    <section className="auth-panel"><div className="eyebrow">WELCOME TO MOTORHAUS</div><h2>{register ? 'Create your account' : 'Welcome back.'}</h2><p className="muted mb-7">{register ? 'Your next vehicle starts here.' : 'Sign in to explore the latest inventory.'}</p>
      {notice && <Notice>{notice}</Notice>}{error && <Notice error>{error}</Notice>}
      <form onSubmit={submit} className="space-y-5"><fieldset disabled={busy} className="space-y-5">
        {register && <label>Full name<input name="full_name" autoComplete="name" required maxLength={100} placeholder="Alex Morgan" /></label>}
        <label>Email address<input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com" /></label>
        <label>Password<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 12 : 1} maxLength={128} />{register && <small>Use 12–128 characters.</small>}</label>
        <button className="primary w-full" type="submit">{busy ? 'Please wait…' : register ? 'Create account ↗' : 'Sign in ↗'}</button>
      </fieldset></form>
      <p className="mt-6 text-sm muted">{register ? 'Already have an account? ' : 'New to Motorhaus? '}<a className="inline-link" href={register ? '#/login' : '#/register'}>{register ? 'Sign in' : 'Create an account'}</a></p>
    </section>
  </main>
}

type Filters = { make: string; model: string; category: string; min_price: string; max_price: string }
const emptyFilters: Filters = { make: '', model: '', category: '', min_price: '', max_price: '' }
function Dashboard({ session, expire }: { session: Session; expire: () => void }) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [filters, setFilters] = useState(emptyFilters)
  const [query, setQuery] = useState('')
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)
  const [editor, setEditor] = useState<Vehicle | 'new' | null>(null)
  const [purchase, setPurchase] = useState<Vehicle | null>(null)
  const [deleting, setDeleting] = useState<Vehicle | null>(null)
  const isAdmin = session.role === 'admin'
  const expireRef = useRef(expire); expireRef.current = expire
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    api<Vehicle[]>(query ? `/vehicles/search?${query}` : '/vehicles', session.token, { signal: controller.signal })
      .then(setVehicles).catch(err => {
        if (controller.signal.aborted) return
        if (err instanceof ApiError && err.status === 401) expireRef.current()
        else setError(message(err))
      }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [session.token, query, revision])
  async function mutate(path: string, method: string, body?: unknown) {
    try { return await api<Vehicle>(path, session.token, { method, ...(body ? { body: JSON.stringify(body) } : {}) }) }
    catch (err) { if (err instanceof ApiError && err.status === 401) expireRef.current(); throw err }
  }
  function refresh(text: string) { setSuccess(text); setRevision(value => value + 1) }
  async function confirmAction(vehicle: Vehicle, remove: boolean) {
    setBusy(true); setError(''); setSuccess('')
    try {
      await mutate(`/vehicles/${vehicle.id}${remove ? '' : '/purchase'}`, remove ? 'DELETE' : 'POST')
      refresh(remove ? 'Vehicle deleted.' : `Purchase successful. One ${vehicle.make} ${vehicle.model} purchased.`)
    } catch (err) { setError(message(err)); if (err instanceof ApiError && err.status === 409) setVehicles(items => items.map(item => item.id === vehicle.id ? { ...item, quantity: 0 } : item)) }
    finally { setBusy(false); setPurchase(null); setDeleting(null) }
  }
  function search(event: FormEvent) {
    event.preventDefault(); setSuccess('')
    if (filters.min_price && filters.max_price && Number(filters.min_price) > Number(filters.max_price)) { setError('Minimum price cannot exceed maximum price.'); return }
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()) })
    setQuery(params.toString()); setRevision(value => value + 1)
  }
  return <main id="main" className="dashboard">
    <section className="page-heading"><div><div className="eyebrow">THE MOTORHAUS COLLECTION</div><h1>Find your next drive<span>.</span></h1><p className="muted">Explore the inventory. Find a vehicle that moves you.</p></div>{isAdmin && <button className="primary" onClick={() => setEditor('new')}>+ Add vehicle</button>}</section>
    <section className="stats" aria-label="Current results"><div><span>Vehicles in view</span><strong>{loading || error ? '—' : String(vehicles.length).padStart(2, '0')}</strong></div><div><span>Units in stock</span><strong>{loading || error ? '—' : vehicles.reduce((sum, vehicle) => sum + vehicle.quantity, 0)}</strong></div><div className="stat-note"><span className="dot" /><p>One collection.<br /><strong>More possibilities.</strong></p></div></section>
    <div className="inventory-layout"><aside className="filter-panel"><div className="flex justify-between items-center mb-5"><h2>Find your fit</h2><span aria-hidden="true">☷</span></div><form onSubmit={search} className="space-y-4"><fieldset disabled={busy} className="space-y-4">
      {(['make', 'model', 'category'] as const).map(key => <label key={key}>{key[0].toUpperCase() + key.slice(1)}<input value={filters[key]} onChange={event => setFilters({ ...filters, [key]: event.target.value })} maxLength={key === 'category' ? 50 : 100} placeholder={key === 'make' ? 'e.g. Toyota' : key === 'model' ? 'e.g. Corolla' : 'e.g. Sedan'} /></label>)}
      <div className="grid grid-cols-2 gap-3">{(['min_price', 'max_price'] as const).map(key => <label key={key}>{key === 'min_price' ? 'Min price' : 'Max price'}<input type="number" min="0" max="9999999999.99" step="0.01" placeholder="Any" value={filters[key]} onChange={event => setFilters({ ...filters, [key]: event.target.value })} /></label>)}</div>
      <small>Make, model and category use exact matches, ignoring case.</small><button className="primary w-full" type="submit">Apply filters</button><button type="button" className="text-button w-full" onClick={() => { setFilters(emptyFilters); setQuery(''); setRevision(v => v + 1); setSuccess('') }}>Clear filters</button>
    </fieldset></form></aside>
    <section className="min-w-0" aria-label="Vehicle inventory"><div className="results-heading"><h2>{query ? 'Your search results' : 'Available collection'}</h2><span>{loading ? 'Updating…' : `${vehicles.length} vehicles`}</span></div>
      {error && <Notice error>{error} <button className="inline-link" onClick={() => setRevision(v => v + 1)}>Refresh inventory</button></Notice>}{success && <Notice>{success}</Notice>}
      {loading ? <div role="status" className="empty-state"><span className="loading-dot" />Loading the collection…</div> : error ? <div className="empty-state">Inventory could not be updated. Please refresh to continue.</div> : !vehicles.length ? <div className="empty-state"><CarArt /><h3>{query ? 'No matching vehicles' : 'The collection is getting ready'}</h3><p>{query ? 'Try a different make, category or price range.' : isAdmin ? 'Add your first vehicle to get started.' : 'There are no vehicles listed yet. Please check back soon.'}</p></div> : <div className="vehicle-grid">{vehicles.map(vehicle => <article key={vehicle.id} className="vehicle-card" aria-label={`${vehicle.make} ${vehicle.model}`}>
        <div className="vehicle-visual"><span className="category-tag">{vehicle.category}</span><CarArt /><span className="illustration-label">VEHICLE ILLUSTRATION</span></div>
        <div className="card-body"><div className="flex justify-between gap-2 items-center"><span className="vehicle-year">{vehicle.year || 'Year not specified'}</span><span className={vehicle.quantity ? 'stock' : 'stock out'}>{vehicle.quantity ? `${vehicle.quantity} in stock` : 'Out of stock'}</span></div><h3>{vehicle.make} {vehicle.model}</h3><div className="price-row"><strong>{money(vehicle.price)}</strong><span>Price · ID {vehicle.id}</span></div>
        <button className="primary w-full" disabled={!vehicle.quantity || busy} onClick={() => setPurchase(vehicle)}>{vehicle.quantity ? 'Purchase vehicle ↗' : 'Currently unavailable'}</button>
        {isAdmin && <div className="admin-actions"><button className="text-button" onClick={() => setEditor(vehicle)} disabled={busy}>Edit vehicle</button><button className="danger-link" onClick={() => setDeleting(vehicle)} disabled={busy}>Delete</button></div>}</div>
      </article>)}</div>}
    </section></div>
    {editor && <VehicleEditor vehicle={editor === 'new' ? null : editor} close={() => setEditor(null)} save={async data => { await mutate(editor === 'new' ? '/vehicles' : `/vehicles/${editor.id}`, editor === 'new' ? 'POST' : 'PUT', data); setEditor(null); refresh('Vehicle saved.') }} />}
    {(purchase || deleting) && <Modal title={deleting ? 'Delete this vehicle?' : 'Confirm your purchase'} close={() => { if (!busy) { setPurchase(null); setDeleting(null) } }} busy={busy}><p className="muted mb-6">{deleting ? `${deleting.make} ${deleting.model} will be permanently removed from inventory.` : `Purchase one ${purchase!.make} ${purchase!.model} at the listed price of ${money(purchase!.price)}?`}</p><div className="flex justify-end gap-3"><button className="secondary" disabled={busy} onClick={() => { setPurchase(null); setDeleting(null) }}>Cancel</button><button className={deleting ? 'danger' : 'primary'} disabled={busy} onClick={() => confirmAction((deleting || purchase)!, Boolean(deleting))}>{busy ? 'Processing…' : deleting ? 'Confirm delete' : 'Confirm purchase'}</button></div></Modal>}
  </main>
}

function Modal({ title, children, close, busy = false }: { title: string; children: ReactNode; close: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = ref.current!; dialog.showModal(); return () => dialog.close() }, [])
  return <dialog ref={ref} className="modal" aria-labelledby="modal-title" onCancel={event => { event.preventDefault(); if (!busy) close() }}><div className="flex items-center justify-between gap-4 mb-6"><h2 id="modal-title">{title}</h2><button className="text-button" aria-label="Close dialog" disabled={busy} onClick={close}>✕</button></div>{children}</dialog>
}

function VehicleEditor({ vehicle, save, close }: { vehicle: Vehicle | null; save: (data: VehicleInput) => Promise<void>; close: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const data = new FormData(event.currentTarget)
    const payload: VehicleInput = { make: String(data.get('make')).trim(), model: String(data.get('model')).trim(), category: String(data.get('category')).trim(), price: String(data.get('price')), quantity: Number(data.get('quantity')), year: data.get('year') ? Number(data.get('year')) : null }
    try { await save(payload) } catch (err) { setError(message(err)); setBusy(false) }
  }
  return <Modal title={vehicle ? 'Edit vehicle' : 'Add a vehicle'} close={close} busy={busy}>{error && <Notice error>{error}</Notice>}<form onSubmit={submit}><fieldset disabled={busy} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
    {(['make', 'model', 'category'] as const).map(key => <label key={key}>{key[0].toUpperCase() + key.slice(1)}<input name={key} required maxLength={key === 'category' ? 50 : 100} defaultValue={vehicle?.[key]} /></label>)}
    <label>Year (optional)<input name="year" type="number" min="1886" max={new Date().getUTCFullYear() + 1} step="1" defaultValue={vehicle?.year || ''} /></label>
    <label>Price<input name="price" type="number" min="0.01" max="9999999999.99" step="0.01" required defaultValue={vehicle?.price} /></label>
    <label>Quantity in stock<input name="quantity" type="number" min="0" max="2147483647" step="1" required defaultValue={vehicle?.quantity ?? 0} /></label>
    <div className="flex justify-end gap-3 sm:col-span-2 mt-3"><button className="secondary" type="button" onClick={close}>Cancel</button><button className="primary" type="submit">{busy ? 'Saving…' : 'Save vehicle'}</button></div>
  </fieldset></form></Modal>
}
