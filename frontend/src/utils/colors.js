const TONES = [
  { hue: 202, sat: 96, light: 66 },
  { hue: 164, sat: 67, light: 60 },
  { hue: 258, sat: 90, light: 76 },
  { hue: 40, sat: 91, light: 67 },
  { hue: 336, sat: 92, light: 73 },
  { hue: 190, sat: 84, light: 58 },
  { hue: 18, sat: 91, light: 67 },
  { hue: 117, sat: 58, light: 62 },
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
    color: `hsl(${tone.hue} ${tone.sat}% ${tone.light}%)`,
    border: `hsla(${tone.hue}, ${tone.sat}%, ${tone.light}%, 0.34)`,
    background: `hsla(${tone.hue}, ${tone.sat}%, ${tone.light}%, 0.13)`,
    backgroundStrong: `hsla(${tone.hue}, ${tone.sat}%, ${tone.light}%, 0.22)`,
    glow: `hsla(${tone.hue}, ${tone.sat}%, ${tone.light}%, 0.2)`,
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
