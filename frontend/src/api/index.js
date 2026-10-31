import { apiRequest, buildQuery } from './http'

export const todosApi = {
  list(params = {}) {
    return apiRequest(`/todos${buildQuery(params)}`)
  },
  create(payload) {
    return apiRequest('/todos', { method: 'POST', body: payload })
  },
  update(id, payload) {
    return apiRequest(`/todos/${id}`, { method: 'PATCH', body: payload })
  },
  remove(id) {
    return apiRequest(`/todos/${id}`, { method: 'DELETE' })
  },
}

export const ledgerApi = {
  list(params = {}) {
    return apiRequest(`/ledger/transactions${buildQuery(params)}`)
  },
  summary(params = {}) {
    return apiRequest(`/ledger/summary${buildQuery(params)}`)
  },
  create(payload) {
    return apiRequest('/ledger/transactions', { method: 'POST', body: payload })
  },
  update(id, payload) {
    return apiRequest(`/ledger/transactions/${id}`, { method: 'PATCH', body: payload })
  },
  remove(id) {
    return apiRequest(`/ledger/transactions/${id}`, { method: 'DELETE' })
  },
}

export const schedulesApi = {
  list(params = {}) {
    return apiRequest(`/schedules${buildQuery(params)}`)
  },
  create(payload) {
    return apiRequest('/schedules', { method: 'POST', body: payload })
  },
  update(id, payload) {
    return apiRequest(`/schedules/${id}`, { method: 'PATCH', body: payload })
  },
  remove(id) {
    return apiRequest(`/schedules/${id}`, { method: 'DELETE' })
  },
}

export const diaryApi = {
  list(params = {}) {
    return apiRequest(`/diary/entries${buildQuery(params)}`)
  },
  byDate(date) {
    return apiRequest(`/diary/entries/by-date/${encodeURIComponent(date)}`)
  },
  create(payload) {
    return apiRequest('/diary/entries', { method: 'POST', body: payload })
  },
  update(id, payload) {
    return apiRequest(`/diary/entries/${id}`, { method: 'PATCH', body: payload })
  },
  remove(id) {
    return apiRequest(`/diary/entries/${id}`, { method: 'DELETE' })
  },
}

export const timetablesApi = {
  list() {
    return apiRequest('/timetables')
  },
  active() {
    return apiRequest('/timetables/active')
  },
  dashboard({ date, timetableId } = {}) {
    return apiRequest(
      `/timetables/dashboard${buildQuery({ date, timetable_id: timetableId })}`,
    )
  },
  update(id, payload) {
    return apiRequest(`/timetables/${id}`, { method: 'PATCH', body: payload })
  },
  activate(id) {
    return apiRequest(`/timetables/${id}/activate`, { method: 'POST' })
  },
  remove(id) {
    return apiRequest(`/timetables/${id}`, { method: 'DELETE' })
  },
  import(file, { name, semesterStartDate, setActive = true } = {}) {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    if (semesterStartDate) form.append('semester_start_date', semesterStartDate)
    form.append('set_active', String(setActive))
    return apiRequest('/timetables/import', {
      method: 'POST',
      body: form,
      timeout: 30000,
    })
  },
}
