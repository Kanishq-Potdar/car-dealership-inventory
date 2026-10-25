import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, readToken } from './api'
import type { Session } from './api'
import Dashboard from './Dashboard'
import { CarArt, Notice } from './ui'

const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.'
function savedSession() { try { return readToken(sessionStorage.getItem('dealership-token') || '') } catch { return null } }

function Brand() { return <a href="#/" className="brand" aria-label="Motorhaus home"><span className="brand-mark">M<span>↗</span></span><span>MOTORHAUS<small>THE DEALERSHIP COLLECTION</small></span></a> }

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
