<script setup>
import {
  AppWindow,
  BookOpen,
  CalendarClock,
  CalendarDays,
  Clock3,
  EyeOff,
  GraduationCap,
  ListTodo,
  Lock,
  StickyNote,
  Unlock,
  Wallet,
} from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import brandMark from '@/assets/brand-mark.svg'
import { toneStyle } from '@/utils/colors'
import {
  WEEKDAYS_CN,
  formatClock,
  formatTime,
} from '@/utils/date'
import { formatMoney } from '@/utils/money'

import { DEFAULT_BLOCKS, blockMeta, cloneBlocks, normalizeBlocks } from './boardConfig'
import { useBoardData } from './useBoardData'

const bridge = window.desktop?.floating || null
const boardMaxWidth = Math.max(560, (window.screen?.availWidth || 1280) - 48)
const {
  now,
  online,
  loading,
  data,
  todayCourses,
  currentCourse,
  nextCourse,
  focalSchedule,
  scheduleIsNow,
  pendingCount,
  nextTodo,
  diaryToday,
  refresh,
} = useBoardData()

const blocks = ref(cloneBlocks(DEFAULT_BLOCKS))
const locked = ref(false)
const shell = ref(null)
const board = ref(null)
let resizeObserver = null
let unsubscribeState = null
let unsubscribeConfig = null
let lastSize = ''

const icons = {
  clock: Clock3,
  date: CalendarDays,
  currentCourse: GraduationCap,
  todayCourses: CalendarDays,
  pendingTodos: ListTodo,
  nextSchedule: CalendarClock,
  monthlyFinance: Wallet,
  diaryStatus: BookOpen,
  custom: StickyNote,
}

function applyState(state) {
  if (!state) return
  blocks.value = normalizeBlocks(state.blocks)
  locked.value = Boolean(state.locked)
}

function courseSubtitle(course) {
  return [
    `${course.start_time.slice(0, 5)}–${course.end_time.slice(0, 5)}`,
    course.location,
  ]
    .filter(Boolean)
    .join(' · ')
}

function makeWidget(block) {
  const meta = blockMeta(block.type)
  const base = {
    id: block.id,
    type: block.type,
    icon: icons[block.type] || StickyNote,
    label: meta.label,
    value: '',
    sub: '',
    title: meta.label,
    tone: toneStyle(block.type),
  }

  if (block.type === 'clock') {
    return {
      ...base,
      label: '现在',
      value: formatClock(now.value),
      sub: `${WEEKDAYS_CN[now.value.getDay()]} · ${now.value.getFullYear()}`,
    }
  }

  if (block.type === 'date') {
    return {
      ...base,
      label: WEEKDAYS_CN[now.value.getDay()],
      value: `${now.value.getMonth() + 1} 月 ${now.value.getDate()} 日`,
      sub: `${now.value.getFullYear()} 年`,
    }
  }

  if (block.type === 'currentCourse') {
    if (loading.value) return { ...base, label: '课程', value: '同步中…' }
    if (currentCourse.value) {
      return {
        ...base,
        label: '正在上课',
        value: currentCourse.value.course_name,
        sub: courseSubtitle(currentCourse.value),
        title: currentCourse.value.course_name,
      }
    }
    if (nextCourse.value) {
      return {
        ...base,
        label: '下一节',
        value: nextCourse.value.course_name,
        sub: courseSubtitle(nextCourse.value),
        title: nextCourse.value.course_name,
      }
    }
    return {
      ...base,
      label: '课程',
      value: data.timetable ? '今日无课' : '未导入课表',
      sub: data.timetable?.current_week
        ? `第 ${data.timetable.current_week} 周`
        : '',
    }
  }

  if (block.type === 'todayCourses') {
    if (loading.value) return { ...base, value: '同步中…' }
    const next = nextCourse.value
    return {
      ...base,
      value: `${todayCourses.value.length} 节`,
      sub: next
        ? `${next.start_time.slice(0, 5)} ${next.course_name}`
        : data.timetable
          ? '今日课程已结束'
          : '未导入课表',
    }
  }

  if (block.type === 'pendingTodos') {
    if (loading.value) return { ...base, value: '同步中…' }
    return {
      ...base,
      value: `${pendingCount.value} 项`,
      sub: nextTodo.value?.title || '清单已清空',
      title: nextTodo.value?.title || '待办清单已清空',
    }
  }

  if (block.type === 'nextSchedule') {
    if (loading.value) return { ...base, value: '同步中…' }
    if (!focalSchedule.value) {
      return {
        ...base,
        label: '日程',
        value: '今日无日程',
        sub: '留一点空白给自己',
      }
    }
    const schedule = focalSchedule.value
    return {
      ...base,
      label: scheduleIsNow.value ? '进行中' : '下一日程',
      value: schedule.title,
      sub: `${formatTime(schedule.start_at)}–${formatTime(schedule.end_at)}${
        schedule.location ? ` · ${schedule.location}` : ''
      }`,
      title: schedule.description || schedule.title,
    }
  }

  if (block.type === 'monthlyFinance') {
    if (loading.value) return { ...base, value: '同步中…' }
    return {
      ...base,
      value: formatMoney(data.ledger?.expense_cents || 0),
      sub: `收入 ${formatMoney(data.ledger?.income_cents || 0)}`,
    }
  }

  if (block.type === 'diaryStatus') {
    if (loading.value) return { ...base, value: '同步中…' }
    return {
      ...base,
      value: diaryToday.value ? '已记录' : '未记录',
      sub: diaryToday.value?.title || '留一句话给今天',
    }
  }

  return {
    ...base,
    label: '便签',
    value: block.text || '在设置中添加文字',
    sub: '',
    title: block.text || '自定义便签',
  }
}

const widgets = computed(() => blocks.value.map(makeWidget))

function reportSize() {
  if (!bridge || !shell.value) return
  const rect = shell.value.getBoundingClientRect()
  const width = Math.ceil(rect.width)
  const height = Math.ceil(rect.height)
  const size = `${width}x${height}`
  if (size === lastSize) return
  lastSize = size
  bridge.resize({ width, height })
}

watch(
  blocks,
  async () => {
    await nextTick()
    reportSize()
  },
  { deep: true },
)

async function toggleLock() {
  if (!bridge) return
  try {
    const state = await bridge.setLocked(!locked.value)
    applyState(state)
  } catch {
    // Keep the board usable even if the window state cannot be updated.
  }
}

async function hideBoard() {
  await bridge?.hide()
}

function openMain() {
  bridge?.openMain()
}

onMounted(async () => {
  if (bridge) {
    try {
      applyState(await bridge.getState())
      unsubscribeState = bridge.onStateChanged(applyState)
      unsubscribeConfig = bridge.onConfigChanged(applyState)
    } catch {
      // Use the default arrangement if state cannot be loaded.
    }
  }

  await nextTick()
  if (shell.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(reportSize)
    resizeObserver.observe(shell.value)
  }
  reportSize()
  window.addEventListener('resize', reportSize)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  unsubscribeState?.()
  unsubscribeConfig?.()
  window.removeEventListener('resize', reportSize)
})
</script>

<template>
  <main
    ref="shell"
    class="floating-shell"
    :style="{ '--board-max-width': `${boardMaxWidth}px` }"
  >
    <section
      ref="board"
      class="floating-board"
      :class="{ 'floating-board--locked': locked }"
      :title="online ? 'Life Assistant 桌面浮窗' : '后端服务离线，显示的是最近一次数据'"
      @dblclick="openMain"
    >
      <div class="board-brand">
        <img :src="brandMark" alt="" />
        <span
          class="board-status"
          :class="{ 'board-status--offline': !online }"
          :title="online ? '服务在线' : '服务离线'"
        ></span>
      </div>

      <div class="board-divider"></div>

      <div class="board-widgets">
        <div
          v-for="widget in widgets"
          :key="widget.id"
          class="floating-widget"
          :class="`floating-widget--${widget.type}`"
          :style="widget.tone"
          :title="widget.title"
        >
          <span class="widget-icon">
            <component :is="widget.icon" :size="14" :stroke-width="1.8" />
          </span>
          <span class="widget-copy">
            <span class="widget-label">{{ widget.label }}</span>
            <strong class="widget-value">{{ widget.value }}</strong>
            <span v-if="widget.sub" class="widget-sub">{{ widget.sub }}</span>
          </span>
        </div>
      </div>

      <div v-if="bridge" class="board-tools">
        <button
          class="board-tool"
          type="button"
          :title="locked ? '解锁拖动' : '锁定位置'"
          @click="toggleLock"
        >
          <Lock v-if="locked" :size="13" />
          <Unlock v-else :size="13" />
        </button>
        <button class="board-tool" type="button" title="打开主界面" @click="openMain">
          <AppWindow :size="13" />
        </button>
        <button class="board-tool" type="button" title="隐藏浮窗" @click="hideBoard">
          <EyeOff :size="13" />
        </button>
      </div>
      <button
        v-else
        class="board-tool board-tool--refresh"
        type="button"
        title="刷新数据"
        @click="refresh"
      >
        <CalendarClock :size="13" />
      </button>
    </section>
  </main>
</template>

<style scoped>
*,
*::before,
*::after {
  box-sizing: border-box;
}

.floating-shell {
  display: flex;
  width: max-content;
  max-width: calc(var(--board-max-width, 1232px) + 20px);
  min-width: 280px;
  padding: 10px;
  background: transparent;
}

.floating-board {
  display: flex;
  width: fit-content;
  max-width: var(--board-max-width, 1232px);
  min-height: 54px;
  align-items: stretch;
  padding: 5px 6px 5px 8px;
  border: 1px solid #dbe7df;
  border-radius: 17px;
  color: var(--text-1);
  background: #ffffff;
  box-shadow: 0 7px 18px rgba(32, 52, 42, 0.12);
  font-family: var(--font-sans);
  user-select: none;
  -webkit-app-region: drag;
}

.floating-board--locked {
  -webkit-app-region: no-drag;
}

.board-brand {
  position: relative;
  display: flex;
  width: 38px;
  flex: none;
  align-items: center;
  justify-content: center;
}

.board-brand img {
  width: 22px;
  height: 22px;
}

.board-status {
  position: absolute;
  right: 5px;
  bottom: 8px;
  width: 6px;
  height: 6px;
  border: 1.5px solid #ffffff;
  border-radius: 50%;
  background: #47ad81;
}

.board-status--offline {
  background: #d55c6c;
}

.board-divider {
  width: 1px;
  flex: none;
  margin: 8px 4px 8px 0;
  background: #e6eee8;
}

.board-widgets {
  display: flex;
  min-width: 0;
  flex: 0 1 auto;
  flex-wrap: wrap;
  align-content: center;
}

.floating-widget {
  display: flex;
  flex: none;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border-right: 1px solid #e9f0ea;
  overflow: hidden;
}

.board-widgets .floating-widget:last-child {
  border-right: 0;
}

.widget-icon {
  display: grid;
  width: 25px;
  height: 25px;
  flex: none;
  place-items: center;
  border-radius: 8px;
  color: var(--tone, #3f8f6c);
  background: var(--tone-bg, #e9f5ee);
}

.widget-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  line-height: 1.18;
}

.widget-label {
  color: var(--text-3);
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.widget-value {
  max-width: 148px;
  margin-top: 1px;
  overflow: hidden;
  color: var(--text-1);
  font-size: 10.5px;
  font-weight: 620;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.widget-sub {
  max-width: 148px;
  margin-top: 1px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.floating-widget--clock {
  width: 124px;
}

.floating-widget--clock .widget-value {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
}

.floating-widget--date {
  width: 124px;
}

.floating-widget--currentCourse {
  width: 192px;
}

.floating-widget--todayCourses {
  width: 156px;
}

.floating-widget--pendingTodos {
  width: 168px;
}

.floating-widget--nextSchedule {
  width: 180px;
}

.floating-widget--monthlyFinance {
  width: 140px;
}

.floating-widget--diaryStatus {
  width: 152px;
}

.floating-widget--custom {
  width: 184px;
}

.floating-widget--custom .widget-value {
  color: var(--tone);
}

.board-tools {
  display: flex;
  flex: none;
  align-items: center;
  gap: 1px;
  margin-left: 3px;
  padding-left: 3px;
  border-left: 1px solid #e9f0ea;
  -webkit-app-region: no-drag;
}

.board-tool {
  display: grid;
  width: 25px;
  height: 29px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  opacity: 0.72;
  transition:
    background 140ms ease,
    color 140ms ease,
    opacity 140ms ease;
}

.board-tool:hover {
  color: var(--accent-deep);
  background: var(--accent-soft);
  opacity: 1;
}

.board-tool--refresh {
  align-self: center;
  margin-left: 3px;
}

@media (max-width: 720px) {
  .floating-shell {
    padding: 7px;
  }
}
</style>
