const BASE_URL = '/api/v1'

async function request(path, options = {}) {
  const headers = { ...options.headers }
  if (options.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

// Trending
export const trendingApi = {
  list: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/trending/${q ? '?' + q : ''}`)
  },
  triggerMonitor: () => request('/trending/monitor/trigger', { method: 'POST' }),
}

// Keywords
export const keywordsApi = {
  list: () => request('/keywords/'),
  create: (data) => request('/keywords/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/keywords/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id) => request(`/keywords/${id}`, { method: 'DELETE' }),
}

// Settings
export const settingsApi = {
  get: () => request('/settings/'),
  update: (data) => request('/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
}

// Notifications
export const notificationsApi = {
  list: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/notifications/${q ? '?' + q : ''}`)
  },
  testEmail: () => request('/notifications/test-email', { method: 'POST' }),
  dailySummary: () => request('/notifications/daily-summary', { method: 'POST' }),
}
