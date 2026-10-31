export const ACCENTS = [
  { id: 'mint', label: '薄荷绿', color: '#3FA980' },
  { id: 'sky', label: '海盐蓝', color: '#4F9FC7' },
  { id: 'peach', label: '蜜桃橙', color: '#E08B6D' },
  { id: 'lilac', label: '雾紫', color: '#9A83C9' },
  { id: 'butter', label: '奶油黄', color: '#C69A3D' },
]

const ACCENT_STORAGE_KEY = 'pla.accent'

export function getStoredAccent() {
  const stored = localStorage.getItem(ACCENT_STORAGE_KEY)
  return ACCENTS.some((accent) => accent.id === stored) ? stored : 'mint'
}

export function applyAccent(id) {
  const accent = ACCENTS.some((item) => item.id === id) ? id : 'mint'
  document.documentElement.dataset.accent = accent
  localStorage.setItem(ACCENT_STORAGE_KEY, accent)
  return accent
}
