const TONES = [
  { color: '#2f7d5f', border: '#c5e3d5', background: '#e7f4ed', strong: '#d9eee4' },
  { color: '#3d7f9f', border: '#c7e0ec', background: '#e8f3f8', strong: '#dceef6' },
  { color: '#79649f', border: '#ddd2ee', background: '#f1ecf8', strong: '#e9e1f5' },
  { color: '#997028', border: '#ebdab5', background: '#faf2de', strong: '#f5e9cf' },
  { color: '#a75467', border: '#f0cad2', background: '#fbe9ed', strong: '#f7dde3' },
  { color: '#2c7e7c', border: '#c2e4e2', background: '#e5f4f3', strong: '#d8eeec' },
  { color: '#a45f38', border: '#eed3c3', background: '#faeee7', strong: '#f5e3d8' },
  { color: '#6e7c33', border: '#dce4c2', background: '#f1f4e5', strong: '#e9efd8' },
]

export function hashString(value) {
  let hash = 0
  for (const character of String(value ?? '')) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  }
  return hash
}

export function toneFor(value) {
  const tone = TONES[hashString(value) % TONES.length]
  return {
    color: tone.color,
    border: tone.border,
    background: tone.background,
    backgroundStrong: tone.strong,
    glow: 'transparent',
  }
}

export function toneStyle(value) {
  const tone = toneFor(value)
  return {
    '--tone': tone.color,
    '--tone-border': tone.border,
    '--tone-bg': tone.background,
    '--tone-bg-strong': tone.backgroundStrong,
    '--tone-glow': tone.glow,
  }
}

export const MOODS = [
  { value: 'great', label: '很好', emoji: '☀️' },
  { value: 'good', label: '不错', emoji: '🌤️' },
  { value: 'neutral', label: '平静', emoji: '🌥️' },
  { value: 'bad', label: '低落', emoji: '🌧️' },
  { value: 'awful', label: '很差', emoji: '⛈️' },
]

export function moodMeta(value) {
  return MOODS.find((mood) => mood.value === value) || null
}

export const WEATHER_OPTIONS = ['晴', '多云', '阴', '小雨', '大雨', '雪', '风']
