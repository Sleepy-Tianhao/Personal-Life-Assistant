const formatter = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatMoney(cents, { sign = false, symbol = true } = {}) {
  const amount = Number(cents || 0) / 100
  const prefix = sign && amount > 0 ? '+' : ''
  return `${prefix}${symbol ? '¥' : ''}${formatter.format(amount)}`
}

export function centsToYuanInput(cents) {
  return (Number(cents || 0) / 100).toFixed(2)
}

export function yuanToCents(value) {
  const amount = Number.parseFloat(String(value).replace(/,/g, ''))
  if (!Number.isFinite(amount) || amount <= 0) return 0
  return Math.round(amount * 100)
}

export function formatCompactMoney(cents) {
  const amount = Number(cents || 0) / 100
  if (Math.abs(amount) >= 10000) {
    return `¥${(amount / 10000).toFixed(1)}万`
  }
  return `¥${formatter.format(amount)}`
}
