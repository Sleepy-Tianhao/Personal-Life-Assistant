export const ACCENTS = [
  { id: 'blue', label: '流光蓝', color: '#59c2ff' },
  { id: 'teal', label: '薄荷青', color: '#58e0c3' },
  { id: 'violet', label: '暮光紫', color: '#b7a4ff' },
  { id: 'rose', label: '晚霞粉', color: '#ff9ac0' },
  { id: 'amber', label: '暖阳金', color: '#f4c96a' },
]

const ACCENT_STORAGE_KEY = 'pla.accent'

export function getStoredAccent() {
  const stored = localStorage.getItem(ACCENT_STORAGE_KEY)
  return ACCENTS.some((accent) => accent.id === stored) ? stored : 'blue'
}

export function applyAccent(id) {
  const accent = ACCENTS.some((item) => item.id === id) ? id : 'blue'
  document.documentElement.dataset.accent = accent
  localStorage.setItem(ACCENT_STORAGE_KEY, accent)
  return accent
}
