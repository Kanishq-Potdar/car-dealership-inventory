import assert from 'node:assert/strict'
import { test } from 'node:test'
import { build } from 'vite'

// Compile the real client with Vite's build-time environment replacement.
// Fetch is stubbed: these tests never contact Render or modify any database.
async function clientFor(base) {
  const result = await build({
    configFile: false, logLevel: 'silent',
    define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify(base) },
    build: { write: false, minify: false, lib: { entry: 'src/api.ts', formats: ['es'] } },
  })
  const bundle = Array.isArray(result) ? result[0] : result
  const code = bundle.output.find(item => item.type === 'chunk').code
  return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
}

for (const base of ['', 'https://car-dealership-inventory-hcpa.onrender.com',
  ' https://car-dealership-inventory-hcpa.onrender.com/ ']) {
  test(`API URL and request behavior with base ${JSON.stringify(base)}`, async t => {
    const { api, ApiError } = await clientFor(base)
    const prefix = base.trim().replace(/\/+$/, '')
    const calls = []
    let response = new Response(JSON.stringify({ ok: true }), { status: 200 })
    t.mock.method(globalThis, 'fetch', async (url, options) => {
      calls.push({ url, options })
      return response
    })
    assert.deepEqual(await api('/auth/login', undefined, { method: 'POST', body: '{"example":true}' }), { ok: true })
    assert.equal(calls[0].url, prefix + '/api/auth/login')
    assert.equal(calls[0].options.method, 'POST')
    assert.equal(calls[0].options.headers['Content-Type'], 'application/json')
    assert.equal(calls[0].options.headers.Authorization, undefined)
    assert.equal(calls[0].options.body, '{"example":true}')
    response = new Response('[]')
    const signal = new AbortController().signal
    await api('/vehicles/search?makes=Toyota&makes=Honda&q=cor&min_price=10', 'test-only-token', { signal })
    assert.equal(calls[1].url, prefix + '/api/vehicles/search?makes=Toyota&makes=Honda&q=cor&min_price=10')
    assert.equal(calls[1].options.headers.Authorization, 'Bearer test-only-token')
    assert.equal(calls[1].options.signal, signal)
    response = new Response(null, { status: 204 })
    assert.equal(await api('/vehicles/1', 'test-only-token', { method: 'DELETE' }), undefined)
    response = new Response('{"detail":"Invalid credentials"}', { status: 401 })
    await assert.rejects(api('/auth/login'), error => error instanceof ApiError && error.status === 401 && error.message === 'Invalid credentials')
    response = new Response('{"detail":[{"loc":["body","email"],"msg":"Invalid"}]}', { status: 422 })
    await assert.rejects(api('/auth/register'), { message: 'email: Invalid', status: 422 })
    response = new Response('not json', { status: 502 })
    await assert.rejects(api('/vehicles'), { status: 502 })
  })
}

test('network and cancellation error behavior is preserved', async t => {
  const { api, ApiError } = await clientFor('')
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Network failure') })
  await assert.rejects(api('/vehicles'), error => error instanceof ApiError && error.status === 0)
  const aborted = new DOMException('Aborted', 'AbortError')
  fetchMock.mock.mockImplementation(async () => { throw aborted })
  await assert.rejects(api('/vehicles'), error => error === aborted)
})
