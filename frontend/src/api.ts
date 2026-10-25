export type Vehicle = {
  id: number; make: string; model: string; category: string;
  year: number | null; price: string; quantity: number; condition: 'new' | 'used'
}
export type VehicleInput = Omit<Vehicle, 'id'>
export type Session = { token: string; role: string; expires: number }

// Claims are display hints only. FastAPI verifies the signature and current role.
export function readToken(token: string): Session | null {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const claims = JSON.parse(atob(part.padEnd(Math.ceil(part.length / 4) * 4, '=')))
    if (typeof claims.exp !== 'number' || claims.exp * 1000 <= Date.now()) return null
    return { token, role: claims.role, expires: claims.exp * 1000 }
  } catch { return null }
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function api<T>(path: string, token?: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch('/api' + path, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw new ApiError('Unable to reach the server. Check your connection and try again.', 0)
  }
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.detail
    const message = Array.isArray(detail)
      ? detail.map((item: { loc: string[]; msg: string }) => `${item.loc.slice(1).join(' ')}: ${item.msg}`).join('. ')
      : typeof detail === 'string' ? detail : 'The server could not complete this request. Please try again.'
    throw new ApiError(message, response.status)
  }
  return data as T
}
