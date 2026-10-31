export const WEEKDAYS_CN = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
export const WEEKDAYS_MONDAY_FIRST = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const pad = (value) => String(value).padStart(2, '0')

export function parseDateKey(key) {
  if (!key) return null
  const [year, month, day] = String(key).slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

export function toDate(value = new Date()) {
  if (value instanceof Date) return new Date(value)
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return parseDateKey(value)
  }
  return new Date(value)
}

export function startOfDay(value = new Date()) {
  const date = toDate(value)
  date.setHours(0, 0, 0, 0)
  return date
}

export function addDays(value, days) {
  const date = toDate(value)
  date.setDate(date.getDate() + days)
  return date
}

export function startOfWeek(value = new Date()) {
  const date = startOfDay(value)
  const offset = (date.getDay() + 6) % 7
  date.setDate(date.getDate() - offset)
  return date
}

export function endOfWeek(value = new Date()) {
  return addDays(startOfWeek(value), 7)
}

export function startOfMonth(value = new Date()) {
  const date = toDate(value)
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

export function addMonths(value, amount) {
  const date = toDate(value)
  return new Date(date.getFullYear(), date.getMonth() + amount, 1)
}

export function endOfMonthExclusive(value = new Date()) {
  const date = toDate(value)
  return new Date(date.getFullYear(), date.getMonth() + 1, 1)
}

export function dateKey(value = new Date()) {
  const date = toDate(value)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function monthKey(value = new Date()) {
  const date = toDate(value)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`
}

export function weekdayNumber(value = new Date()) {
  return ((toDate(value).getDay() + 6) % 7) + 1
}

export function isoToLocalInput(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${dateKey(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function localInputToIso(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}

export function formatDate(value, options = {}) {
  const date = toDate(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...options,
  }).format(date)
}

export function formatDateLong(value) {
  const date = toDate(value)
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${WEEKDAYS_CN[date.getDay()]}`
}

export function formatMonthTitle(value) {
  const date = toDate(value)
  return `${date.getFullYear()} 年 ${date.getMonth() + 1} 月`
}

export function formatTime(value, withSeconds = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    ...(withSeconds ? { second: '2-digit' } : {}),
    hour12: false,
  }).format(date)
}

export function formatClock(value = new Date()) {
  const date = toDate(value)
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function formatRelativeDay(value) {
  const target = startOfDay(value)
  const today = startOfDay()
  const diff = Math.round((target - today) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  if (diff === -1) return '昨天'
  return `${target.getMonth() + 1}月${target.getDate()}日`
}

export function formatRelativeDayLong(value) {
  const target = startOfDay(value)
  const today = startOfDay()
  const diff = Math.round((target - today) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  if (diff === 2) return '后天'
  return `${target.getMonth() + 1}月${target.getDate()}日 ${WEEKDAYS_CN[target.getDay()]}`
}

export function formatDueDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const prefix = formatRelativeDay(date)
  return `${prefix} ${formatTime(date)}`
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return `${formatDate(date)} ${formatTime(date)}`
}

export function parseTimeToMinutes(value) {
  if (!value) return 0
  const [hour, minute = 0] = String(value).split(':').map(Number)
  return hour * 60 + minute
}

export function minutesToTimeLabel(minutes) {
  const normalized = Math.max(0, Number(minutes) || 0)
  return `${pad(Math.floor(normalized / 60))}:${pad(Math.round(normalized % 60))}`
}

export function isSameDay(a, b) {
  return dateKey(a) === dateKey(b)
}

export function isToday(value) {
  return isSameDay(value, new Date())
}

export function getGreeting(now = new Date()) {
  const hour = now.getHours()
  if (hour < 5) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

export function daysBetween(start, end) {
  return Math.round((startOfDay(end) - startOfDay(start)) / 86400000)
}

export function monthRangeIso(value = new Date()) {
  return {
    start_at: startOfMonth(value).toISOString(),
    end_at: endOfMonthExclusive(value).toISOString(),
  }
}

export function dayRangeIso(value = new Date()) {
  return {
    range_start: startOfDay(value).toISOString(),
    range_end: addDays(startOfDay(value), 1).toISOString(),
  }
}

export function weekRangeIso(value = new Date()) {
  return {
    range_start: startOfWeek(value).toISOString(),
    range_end: endOfWeek(value).toISOString(),
  }
}

export function relativeTimeLabel(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  const diff = Date.now() - date.getTime()
  const minute = 60000
  const hour = 3600000
  const day = 86400000
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < day * 7) return `${Math.floor(diff / day)} 天前`
  return formatDate(date)
}
