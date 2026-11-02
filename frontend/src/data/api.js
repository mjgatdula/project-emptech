// JWT tokens belong to this browser origin. Never log passwords or token values.
const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
let csrfToken = ''
let sessionRequest = null
let refreshRequest = null
let authVersion = 0
let verifiedSession = null
const sessionCacheMs = 30_000

export class ApiError extends Error {
  constructor(message, status = 0) { super(message); this.status = status }
}

function tokens() {
  try {
    return { access: localStorage.getItem('access_token'), refresh: localStorage.getItem('refresh_token') }
  } catch {
    return { access: null, refresh: null }
  }
}

function saveTokens(pair) {
  if (typeof pair.access !== 'string' || !pair.access || typeof pair.refresh !== 'string' || !pair.refresh) {
    throw new ApiError('Django did not return both authentication tokens.')
  }
  try {
    localStorage.setItem('refresh_token', pair.refresh)
    localStorage.setItem('access_token', pair.access)
  } catch {
    clearTokens(false)
    throw new ApiError('Allow site storage in your browser to stay signed in.')
  }
  authVersion += 1
  verifiedSession = null
  sessionRequest = null
}

function clearTokens(notify = true) {
  try {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  } catch { /* Storage may be blocked by the browser. */ }
  authVersion += 1
  verifiedSession = null
  sessionRequest = null
  if (notify) window.dispatchEvent(new Event('tipped:auth-cleared'))
}

async function request(path, { method = 'GET', data, signal, auth = true, responseType = 'json', retryCsrf = true } = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 30000)
  const cancel = () => controller.abort()
  signal?.addEventListener('abort', cancel, { once: true })
  if (signal?.aborted) controller.abort()
  try {
    const headers = { Accept: 'application/json' }
    const access = auth ? tokens().access : null
    if (access) headers.Authorization = `Bearer ${access}`
    const multipart = data instanceof FormData
    if (data !== undefined && !multipart) headers['Content-Type'] = 'application/json'
    if (method !== 'GET' && method !== 'HEAD') headers['X-CSRFToken'] = csrfToken
    const response = await fetch(`${base}/api${path}`, {
      method, headers, credentials: 'include', cache: 'no-store', signal: controller.signal,
      ...(data !== undefined ? { body: multipart ? data : JSON.stringify(data) } : {}),
    })
    if (response.status === 204) return null
    if (response.ok && responseType === 'blob') return response.blob()
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
      throw new ApiError('The API did not return JSON. Check Django and the /api proxy.', response.status)
    }
    const payload = await response.json()
    if (payload.csrfToken) csrfToken = payload.csrfToken
    // Django admin login can rotate the cookie while this tab retains an older token.
    // Middleware rejected the first request before executing the account action.
    if (response.status === 403 && payload.code === 'csrf_failed' && retryCsrf && method === 'POST' && path.startsWith('/auth/')) {
      clearTimeout(timeout)
      await request('/auth/session/', { auth: false, signal })
      return request(path, { method, data, signal, auth, responseType, retryCsrf: false })
    }
    if (!response.ok) throw new ApiError(payload.message || payload.detail || 'The request could not be completed.', response.status)
    return payload
  } catch (error) {
    if (error instanceof ApiError || signal?.aborted) throw error
    throw new ApiError(controller.signal.aborted ? 'The server took too long to respond. Please try again.' : 'Could not reach Django. Start the backend on port 8000 and try again.')
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', cancel)
  }
}

async function ensureCsrf() {
  if (!csrfToken) await request('/auth/session/', { auth: false })
}

function refreshTokens() {
  if (refreshRequest) return refreshRequest
  const original = tokens().refresh
  const version = authVersion
  const rotate = async () => {
    // A different tab may have already rotated the pair while this tab waited.
    if (tokens().refresh !== original) {
      if (tokens().access && tokens().refresh) return tokens()
      throw new ApiError('Please sign in again.', 401)
    }
    if (!original) throw new ApiError('Please sign in again.', 401)
    try {
      await ensureCsrf()
      const pair = await request('/auth/refresh/', { method: 'POST', data: { refresh: original }, auth: false })
      if (version !== authVersion || tokens().refresh !== original) throw new ApiError('The sign-in changed. Please try again.', 401)
      saveTokens(pair)
      return pair
    } catch (error) {
      if ((error.status === 401 || error.status === 400) && tokens().refresh === original && version === authVersion) clearTokens()
      throw error
    }
  }
  const work = navigator.locks?.request ? navigator.locks.request('tipped:refresh', rotate) : rotate()
  refreshRequest = Promise.resolve(work).finally(() => { refreshRequest = null })
  return refreshRequest
}

export async function apiRequest(path, options = {}) {
  if (options.auth === false) return request(path, options)
  if (!tokens().access && tokens().refresh) await refreshTokens()
  const access = tokens().access
  try {
    return await request(path, options)
  } catch (error) {
    if (error.status !== 401 || options.signal?.aborted || !access) throw error
    if (!tokens().refresh) { clearTokens(); throw error }
    // A concurrent request may already have renewed the expired access token.
    if (tokens().access === access) await refreshTokens()
    try {
      return await request(path, options)
    } catch (retryError) {
      if (retryError.status === 401) clearTokens()
      throw retryError
    }
  }
}

function cacheSession(result) {
  const pair = tokens()
  verifiedSession = {
    result, access: pair.access, refresh: pair.refresh,
    expiresAt: Date.now() + sessionCacheMs,
  }
}

export function getSession({ force = false } = {}) {
  const pair = tokens()
  if (!force && verifiedSession && verifiedSession.expiresAt > Date.now()
    && verifiedSession.access === pair.access && verifiedSession.refresh === pair.refresh) {
    return Promise.resolve(verifiedSession.result)
  }
  if (sessionRequest) return sessionRequest
  const version = authVersion
  const pending = apiRequest('/auth/session/').catch((error) => {
    if (error.status !== 401) throw error
    // Expired/revoked tokens resolve as signed out, not a server outage.
    return request('/auth/session/', { auth: false })
  }).then((result) => {
    if (version === authVersion && pair.access === tokens().access && pair.refresh === tokens().refresh) cacheSession(result)
    return result
  }).finally(() => { if (sessionRequest === pending) sessionRequest = null })
  sessionRequest = pending
  return pending
}

async function signIn(path, data) {
  await ensureCsrf()
  const version = authVersion
  const result = await request(path, { method: 'POST', data, auth: false })
  if (version !== authVersion) throw new ApiError('The sign-in changed. Please try again.')
  saveTokens(result)
  // Login/registration already verified this account; avoid a second round trip.
  cacheSession(result)
  return result
}

export const authApi = {
  session: getSession,
  signIn: (credentials) => credentials.googleCredential ? signIn('/auth/google/', {credential: credentials.googleCredential}) : signIn('/auth/login/', credentials),
  linkGoogle: async (credential) => {
    await ensureCsrf()
    const result = await apiRequest('/auth/google/', {method:'POST', data:{credential, link:true}})
    saveTokens(result); cacheSession(result); return result
  },
  register: (details) => signIn('/auth/register/', details),
  changePassword: async (data) => {
    await ensureCsrf()
    const result = await apiRequest('/auth/password/', { method: 'POST', data })
    saveTokens(result)
    cacheSession(result)
    return result
  },
  signOut: async () => {
    // Finish any ongoing rotation before revoking the current refresh token.
    if (refreshRequest) {
      try { await refreshRequest } catch { /* Continue with the current pair. */ }
    }
    const refresh = tokens().refresh
    if (refresh) {
      await ensureCsrf()
      await request('/auth/logout/', { method: 'POST', data: { refresh }, auth: false })
    }
    clearTokens(false)
    return { user: null, isAuthenticated: false }
  },
}


export async function downloadFile(path, filename) {
  const blob = await apiRequest(path, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
