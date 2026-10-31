const FALLBACK_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const API_BASE_STORAGE_KEY = 'pla.apiBaseUrl'

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function getApiBaseUrl() {
  return (
    localStorage.getItem(API_BASE_STORAGE_KEY) ||
    import.meta.env.VITE_API_BASE_URL ||
    FALLBACK_BASE_URL
  ).replace(/\/+$/, '')
}

export function setApiBaseUrl(value) {
  const normalized = String(value || '').trim().replace(/\/+$/, '')
  if (normalized) {
    localStorage.setItem(API_BASE_STORAGE_KEY, normalized)
  } else {
    localStorage.removeItem(API_BASE_STORAGE_KEY)
  }
}

export function getServiceBaseUrl() {
  try {
    const url = new URL(getApiBaseUrl())
    url.pathname = url.pathname.replace(/\/api\/v1\/?$/, '')
    return url.toString().replace(/\/+$/, '')
  } catch {
    return getApiBaseUrl()
  }
}

export function buildQuery(params = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') {
          search.append(key, String(item))
        }
      })
    } else {
      search.append(key, String(value))
    }
  }
  const result = search.toString()
  return result ? `?${result}` : ''
}

function detailToMessage(detail) {
  if (!detail) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        const field = Array.isArray(item.loc) ? item.loc.filter((x) => x !== 'body').join('.') : ''
        return `${field ? `${field}: ` : ''}${item.msg || '参数错误'}`
      })
      .join('；')
  }
  if (typeof detail === 'object' && detail.message) return detail.message
  return ''
}

export async function apiRequest(path, options = {}) {
  const { method = 'GET', body, headers = {}, timeout = 15000 } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  const requestHeaders = { Accept: 'application/json', ...headers }
  let requestBody = body

  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    requestHeaders['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      method,
      headers: requestHeaders,
      body: requestBody,
      signal: controller.signal,
    })

    const contentType = response.headers.get('content-type') || ''
    const payload = response.status === 204
      ? null
      : contentType.includes('application/json')
        ? await response.json()
        : await response.text()

    if (!response.ok) {
      const message =
        detailToMessage(payload?.detail) ||
        detailToMessage(payload) ||
        `请求失败（HTTP ${response.status}）`
      throw new ApiError(message, { status: response.status, detail: payload?.detail ?? payload })
    }

    return payload
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') {
      throw new ApiError('请求超时，请检查后端服务是否运行。')
    }
    throw new ApiError(`无法连接后端服务（${getApiBaseUrl()}），请确认 FastAPI 已启动。`)
  } finally {
    clearTimeout(timer)
  }
}

export async function getServiceInfo() {
  const response = await fetch(`${getServiceBaseUrl()}/`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new ApiError('无法获取服务信息', { status: response.status })
  return response.json()
}

export async function checkApiHealth() {
  try {
    const response = await fetch(`${getServiceBaseUrl()}/health`, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(4000),
    })
    return response.ok
  } catch {
    return false
  }
}
