export const MIN_FLOATING_BLOCKS = 1
export const MAX_FLOATING_BLOCKS = 8

export const BLOCK_TYPES = [
  {
    type: 'clock',
    label: '时钟',
    description: '实时时间，带秒针式分钟更新',
  },
  {
    type: 'date',
    label: '日期',
    description: '今天的日期与星期',
  },
  {
    type: 'currentCourse',
    label: '当前课程',
    description: '正在上的课，或下一节课',
  },
  {
    type: 'todayCourses',
    label: '今日课程',
    description: '今日课程数量与下一节',
  },
  {
    type: 'pendingTodos',
    label: '待办事项',
    description: '未完成待办数量与下一项',
  },
  {
    type: 'nextSchedule',
    label: '下一日程',
    description: '今天最近的日程安排',
  },
  {
    type: 'monthlyFinance',
    label: '本月支出',
    description: '本月支出与收入概览',
  },
  {
    type: 'diaryStatus',
    label: '日记状态',
    description: '今天是否已经写日记',
  },
  {
    type: 'custom',
    label: '自定义文字',
    description: '显示一句属于自己的便签',
  },
]

export const BLOCK_TYPE_KEYS = new Set(BLOCK_TYPES.map((item) => item.type))

export function createBlock(type = 'clock') {
  const safeType = BLOCK_TYPE_KEYS.has(type) ? type : 'clock'
  return {
    id:
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `block-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type: safeType,
    text: '',
  }
}

export const DEFAULT_BLOCKS = [
  { id: 'default-clock', type: 'clock', text: '' },
  { id: 'default-date', type: 'date', text: '' },
  { id: 'default-course', type: 'currentCourse', text: '' },
  { id: 'default-todos', type: 'pendingTodos', text: '' },
]

export function cloneBlocks(blocks = DEFAULT_BLOCKS) {
  return blocks.map((block) => ({ ...block }))
}

export function normalizeBlocks(blocks) {
  if (!Array.isArray(blocks) || !blocks.length) return cloneBlocks(DEFAULT_BLOCKS)

  const usedIds = new Set()
  const normalized = []

  for (const [index, block] of blocks.slice(0, MAX_FLOATING_BLOCKS).entries()) {
    if (!block || !BLOCK_TYPE_KEYS.has(block.type)) continue
    let id = String(block.id || `block-${index}`).slice(0, 80)
    while (usedIds.has(id)) id = `${id}-${index}`
    usedIds.add(id)
    normalized.push({
      id,
      type: block.type,
      text: block.type === 'custom' ? String(block.text || '').slice(0, 80) : '',
    })
  }

  return normalized.length ? normalized : cloneBlocks(DEFAULT_BLOCKS)
}

export function blockMeta(type) {
  return BLOCK_TYPES.find((item) => item.type === type) || BLOCK_TYPES[0]
}
