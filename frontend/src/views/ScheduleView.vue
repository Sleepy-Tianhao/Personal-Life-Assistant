<script setup>
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Plus,
  Trash2,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import { schedulesApi } from '@/api'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDialogStore } from '@/stores/dialog'
import { useToastStore } from '@/stores/toast'
import { toneFor, toneStyle } from '@/utils/colors'
import {
  WEEKDAYS_MONDAY_FIRST,
  addDays,
  dateKey,
  formatTime,
  isoToLocalInput,
  localInputToIso,
  startOfWeek,
  weekRangeIso,
} from '@/utils/date'

const START_HOUR = 7
const END_HOUR = 23
const HOUR_HEIGHT = 54
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60

const toast = useToastStore()
const dialog = useDialogStore()

const weekStart = ref(startOfWeek(new Date()))
const schedules = ref([])
const loading = ref(true)
const formOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const now = ref(new Date())

const form = reactive({
  title: '',
  location: '',
  description: '',
  allDay: false,
  startLocal: '',
  endLocal: '',
})

const days = computed(() =>
  Array.from({ length: 7 }, (_, index) => {
    const date = addDays(weekStart.value, index)
    return {
      date,
      key: dateKey(date),
      weekday: WEEKDAYS_MONDAY_FIRST[index],
      dayNumber: date.getDate(),
      month: date.getMonth() + 1,
      isToday: dateKey(date) === dateKey(new Date()),
    }
  }),
)

const weekTitle = computed(() => {
  const start = weekStart.value
  const end = addDays(start, 6)
  if (start.getMonth() === end.getMonth()) {
    return `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日 – ${end.getDate()}日`
  }
  return `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日 – ${end.getMonth() + 1}月${end.getDate()}日`
})

const weekCount = computed(() => schedules.value.length)
const allDayEvents = computed(() => schedules.value.filter((item) => item.all_day))
const timedEvents = computed(() => schedules.value.filter((item) => !item.all_day))

const eventsByDay = computed(() => {
  const result = new Map()
  for (const day of days.value) {
    const dayStart = new Date(day.date)
    dayStart.setHours(0, 0, 0, 0)
    const dayEnd = addDays(dayStart, 1)
    const events = timedEvents.value
      .map((event) => {
        const start = new Date(event.start_at)
        const end = new Date(event.end_at)
        return {
          ...event,
          localStart: start,
          localEnd: end,
          minuteStart: start.getHours() * 60 + start.getMinutes(),
          minuteEnd: end.getHours() * 60 + end.getMinutes(),
          start,
          end,
        }
      })
      .filter((event) => event.start < dayEnd && event.end > dayStart)
      .map((event) => {
        const rangeStart = START_HOUR * 60
        const rangeEnd = END_HOUR * 60
        const clippedStart = Math.max(rangeStart, event.minuteStart)
        const clippedEnd = Math.min(rangeEnd, event.minuteEnd)
        return {
          ...event,
          top: ((clippedStart - rangeStart) / 60) * HOUR_HEIGHT,
          height: Math.max(24, ((clippedEnd - clippedStart) / 60) * HOUR_HEIGHT),
          clippedStart,
          clippedEnd,
          startsBefore: event.minuteStart < rangeStart,
          endsAfter: event.minuteEnd > rangeEnd,
        }
      })
      .filter((event) => event.height > 0)

    result.set(day.key, layoutEvents(events))
  }
  return result
})

const currentLineTop = computed(() => {
  const today = new Date(now.value)
  const minutes = today.getHours() * 60 + today.getMinutes()
  const rangeStart = START_HOUR * 60
  const rangeEnd = END_HOUR * 60
  if (minutes < rangeStart || minutes > rangeEnd) return null
  return ((minutes - rangeStart) / 60) * HOUR_HEIGHT
})

const currentDayKey = computed(() => dateKey(now.value))

const hours = Array.from(
  { length: END_HOUR - START_HOUR },
  (_, index) => START_HOUR + index,
)

const gridStyle = {
  '--hour-height': `${HOUR_HEIGHT}px`,
  '--total-height': `${((END_HOUR - START_HOUR) * HOUR_HEIGHT).toFixed(0)}px`,
}

function layoutEvents(events) {
  const sorted = [...events].sort(
    (a, b) => a.clippedStart - b.clippedStart || a.clippedEnd - b.clippedEnd,
  )
  const groups = []
  let currentGroup = []
  let groupEnd = -1

  for (const event of sorted) {
    if (!currentGroup.length || event.clippedStart < groupEnd) {
      currentGroup.push(event)
      groupEnd = Math.max(groupEnd, event.clippedEnd)
    } else {
      groups.push(currentGroup)
      currentGroup = [event]
      groupEnd = event.clippedEnd
    }
  }
  if (currentGroup.length) groups.push(currentGroup)

  const result = []
  for (const group of groups) {
    const laneEnds = []
    const withLanes = group.map((event) => {
      let lane = laneEnds.findIndex((end) => end <= event.clippedStart)
      if (lane === -1) {
        lane = laneEnds.length
        laneEnds.push(event.clippedEnd)
      } else {
        laneEnds[lane] = event.clippedEnd
      }
      return { ...event, lane }
    })
    const laneCount = laneEnds.length
    withLanes.forEach((event) => result.push({ ...event, laneCount }))
  }
  return result
}

function eventsForDay(day) {
  return eventsByDay.value.get(day.key) || []
}

function allDayForDay(day) {
  const dayStart = new Date(day.date)
  dayStart.setHours(0, 0, 0, 0)
  const dayEnd = addDays(dayStart, 1)
  return allDayEvents.value.filter((event) => {
    const start = new Date(event.start_at)
    const end = new Date(event.end_at)
    return start < dayEnd && end > dayStart
  })
}

function eventStyle(event) {
  return {
    ...toneStyle(event.title),
    top: `${event.top}px`,
    height: `${event.height}px`,
    left: `calc(${(event.lane / event.laneCount) * 100}% + 2px)`,
    width: `calc(${100 / event.laneCount}% - 4px)`,
  }
}

async function loadSchedules() {
  loading.value = true
  try {
    const result = await schedulesApi.list({
      ...weekRangeIso(weekStart.value),
      sort_by: 'start_at',
      sort_order: 'asc',
      limit: 200,
    })
    schedules.value = result.items
  } catch (error) {
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

watch(weekStart, loadSchedules)

function moveWeek(offset) {
  weekStart.value = addDays(weekStart.value, offset * 7)
}

function goThisWeek() {
  weekStart.value = startOfWeek(new Date())
}

function defaultTimes(date = new Date()) {
  const start = new Date(date)
  start.setHours(9, 0, 0, 0)
  const end = new Date(start)
  end.setHours(10, 0, 0, 0)
  return {
    start: isoToLocalInput(start.toISOString()),
    end: isoToLocalInput(end.toISOString()),
  }
}

function resetForm(date = new Date()) {
  const times = defaultTimes(date)
  form.title = ''
  form.location = ''
  form.description = ''
  form.allDay = false
  form.startLocal = times.start
  form.endLocal = times.end
}

function openCreate(date = new Date()) {
  editing.value = null
  resetForm(date)
  formOpen.value = true
}

function openEdit(event) {
  editing.value = event
  form.title = event.title
  form.location = event.location || ''
  form.description = event.description || ''
  form.allDay = event.all_day
  form.startLocal = isoToLocalInput(event.start_at)
  form.endLocal = isoToLocalInput(event.end_at)
  formOpen.value = true
}

function toggleAllDay() {
  const startDate = form.startLocal ? new Date(form.startLocal) : new Date()
  if (form.allDay) {
    const start = new Date(startDate)
    start.setHours(0, 0, 0, 0)
    const end = new Date(startDate)
    end.setHours(23, 59, 0, 0)
    form.startLocal = isoToLocalInput(start.toISOString())
    form.endLocal = isoToLocalInput(end.toISOString())
  }
}

function syncAllDayEnd() {
  if (!form.allDay || !form.startLocal) return
  const start = new Date(form.startLocal)
  const end = new Date(form.startLocal)
  end.setHours(23, 59, 0, 0)
  form.endLocal = isoToLocalInput(end.toISOString())
}

async function saveEvent() {
  if (!form.title.trim()) {
    toast.warning('请填写日程标题')
    return
  }
  if (!form.startLocal || !form.endLocal) {
    toast.warning('请选择开始和结束时间')
    return
  }
  const startAt = localInputToIso(form.startLocal)
  const endAt = localInputToIso(form.endLocal)
  if (new Date(endAt) <= new Date(startAt)) {
    toast.warning('结束时间必须晚于开始时间')
    return
  }

  saving.value = true
  const payload = {
    title: form.title.trim(),
    location: form.location.trim() || null,
    description: form.description.trim() || null,
    start_at: startAt,
    end_at: endAt,
    all_day: form.allDay,
  }

  try {
    if (editing.value) {
      await schedulesApi.update(editing.value.id, payload)
      toast.success('日程已更新')
    } else {
      await schedulesApi.create(payload)
      toast.success('日程已创建')
    }
    formOpen.value = false
    await loadSchedules()
  } catch (error) {
    toast.error(error.message)
  } finally {
    saving.value = false
  }
}

async function deleteEvent(event) {
  const confirmed = await dialog.ask({
    title: '删除日程',
    message: `确定删除「${event.title}」吗？此操作无法撤销。`,
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  try {
    await schedulesApi.remove(event.id)
    toast.success('日程已删除')
    formOpen.value = false
    await loadSchedules()
  } catch (error) {
    toast.error(error.message)
  }
}

let clockTimer = null
onMounted(() => {
  loadSchedules()
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 60000)
})
onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <PageHeader
        eyebrow="SCHEDULE"
        title="日程"
        description="用一周的视角安排时间，重要的事情需要被看见。"
      >
        <template #actions>
          <span class="chip">{{ weekCount }} 项安排</span>
          <div class="week-picker">
            <button class="icon-btn" type="button" title="上一周" @click="moveWeek(-1)">
              <ChevronLeft :size="16" />
            </button>
            <button class="week-label" type="button" @click="goThisWeek">
              {{ weekTitle }}
            </button>
            <button class="icon-btn" type="button" title="下一周" @click="moveWeek(1)">
              <ChevronRight :size="16" />
            </button>
          </div>
          <button class="btn btn-primary" type="button" @click="openCreate(new Date())">
            <Plus :size="15" />
            新建日程
          </button>
        </template>
      </PageHeader>

      <section class="calendar-card card">
        <header class="calendar-head">
          <div class="calendar-heading">
            <span class="eyebrow">WEEK VIEW</span>
            <h2 class="section-title">
              <CalendarDays :size="17" />
              {{ weekTitle }}
            </h2>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="goThisWeek">
            回到本周
          </button>
        </header>

        <div class="week-scroll">
          <div class="week-frame">
            <div class="week-header">
              <div class="week-header__gutter"></div>
          <button
            v-for="day in days"
            :key="day.key"
            class="week-day"
            :class="{ 'week-day--today': day.isToday }"
            type="button"
            @click="openCreate(day.date)"
          >
            <span class="week-day__name">{{ day.weekday }}</span>
            <span class="week-day__number">{{ day.dayNumber }}</span>
            <span class="week-day__month">{{ day.month }}月</span>
            <span class="week-day__add"><Plus :size="12" /></span>
          </button>
        </div>

        <div v-if="allDayEvents.length" class="all-day-row">
          <div class="all-day-label">全天</div>
          <div v-for="day in days" :key="day.key" class="all-day-cell">
            <button
              v-for="event in allDayForDay(day)"
              :key="event.id"
              class="all-day-event"
              :style="toneStyle(event.title)"
              type="button"
              @click="openEdit(event)"
            >
              {{ event.title }}
            </button>
          </div>
        </div>

          <div class="week-body" :style="gridStyle">
            <div class="time-gutter">
              <span
                v-for="hour in hours"
                :key="hour"
                class="time-label"
                :style="{ top: `${(hour - START_HOUR) * HOUR_HEIGHT}px` }"
              >
                {{ String(hour).padStart(2, '0') }}:00
              </span>
            </div>

            <div
              v-for="day in days"
              :key="day.key"
              class="day-column"
              :class="{ 'day-column--today': day.isToday }"
            >
              <span
                v-for="hour in hours"
                :key="hour"
                class="hour-line"
                :style="{ top: `${(hour - START_HOUR) * HOUR_HEIGHT}px` }"
              ></span>

              <span
                v-if="day.isToday && currentLineTop !== null"
                class="current-time-line"
                :style="{ top: `${currentLineTop}px` }"
              >
                <span></span>
              </span>

              <button
                v-for="event in eventsForDay(day)"
                :key="event.id"
                class="event-block"
                :class="{
                  'event-block--compact': event.height < 44,
                  'event-block--clipped-top': event.startsBefore,
                  'event-block--clipped-bottom': event.endsAfter,
                }"
                :style="eventStyle(event)"
                type="button"
                @click="openEdit(event)"
              >
                <span class="event-time">
                  {{ formatTime(event.start_at) }} – {{ formatTime(event.end_at) }}
                </span>
                <strong>{{ event.title }}</strong>
                <span v-if="event.height >= 58 && event.location" class="event-location">
                  <MapPin :size="10" />
                  {{ event.location }}
                </span>
              </button>

              <div v-if="loading" class="column-loading"></div>
            </div>
          </div>
          </div>
        </div>

        <div v-if="!loading && !schedules.length" class="calendar-empty">
          <span class="empty-state__icon"><CalendarDays :size="20" /></span>
          <div>
            <strong>这一周还没有安排</strong>
            <p>点击日期或“新建日程”，为这一周留出几段有意义的专注。</p>
          </div>
          <button class="btn btn-sm" type="button" @click="openCreate(new Date())">
            <Plus :size="14" /> 添加日程
          </button>
        </div>
      </section>
    </div>

    <Modal
      v-model="formOpen"
      :title="editing ? '编辑日程' : '新建日程'"
      :subtitle="editing ? '修改后会立即更新本周视图。' : '安排一段不被打扰的时间。'"
      :width="560"
    >
      <form class="schedule-form" @submit.prevent="saveEvent">
        <div class="field">
          <label for="schedule-title">标题</label>
          <input
            id="schedule-title"
            v-model="form.title"
            class="input"
            maxlength="200"
            placeholder="例如：项目复盘会议"
            autofocus
          />
        </div>

        <div class="field">
          <label for="schedule-location">地点</label>
          <input
            id="schedule-location"
            v-model="form.location"
            class="input"
            maxlength="200"
            placeholder="可选"
          />
        </div>

        <label class="switch all-day-switch">
          <input v-model="form.allDay" type="checkbox" @change="toggleAllDay" />
          <span class="switch__track"></span>
          全天日程
        </label>

        <div class="form-grid">
          <div class="field">
            <label for="schedule-start">开始时间</label>
            <input
              id="schedule-start"
              v-model="form.startLocal"
              class="input"
              type="datetime-local"
              @change="syncAllDayEnd"
            />
          </div>
          <div class="field">
            <label for="schedule-end">结束时间</label>
            <input
              id="schedule-end"
              v-model="form.endLocal"
              class="input"
              type="datetime-local"
            />
          </div>
        </div>

        <div class="field">
          <label for="schedule-description">描述</label>
          <textarea
            id="schedule-description"
            v-model="form.description"
            class="textarea"
            maxlength="5000"
            placeholder="补充议程、准备事项或相关链接…"
          ></textarea>
        </div>

        <button class="form-submit-hidden" type="submit"></button>
      </form>

      <template #footer>
        <button
          v-if="editing"
          class="btn btn-danger footer-delete"
          type="button"
          @click="deleteEvent(editing)"
        >
          <Trash2 :size="14" />
          删除
        </button>
        <span class="footer-spacer"></span>
        <button class="btn" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="saving" @click="saveEvent">
          <span v-if="saving" class="spinner spinner--small"></span>
          {{ editing ? '保存修改' : '创建日程' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.week-picker {
  display: flex;
  height: 38px;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--stroke);
  border-radius: 11px;
  background: var(--surface-2);
}

.week-label {
  min-width: 184px;
  border: 0;
  border-radius: 8px;
  color: var(--text-2);
  background: transparent;
  font-size: 11px;
  font-weight: 570;
  cursor: pointer;
}

.week-label:hover {
  color: var(--text-1);
  background: var(--surface-3);
}

.calendar-card {
  overflow: hidden;
  padding: 20px 20px 0;
}

.calendar-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 18px;
}

.calendar-heading .section-title {
  margin-top: 5px;
}

.week-scroll {
  overflow-x: auto;
}

.week-frame {
  min-width: 880px;
}

.week-header {
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(100px, 1fr));
  border-top: 1px solid var(--stroke);
  border-left: 1px solid var(--stroke);
}

.week-header__gutter {
  border-right: 1px solid var(--stroke);
  border-bottom: 1px solid var(--stroke);
}

.week-day {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  gap: 1px 8px;
  padding: 11px 12px 10px;
  border: 0;
  border-right: 1px solid var(--stroke);
  border-bottom: 1px solid var(--stroke);
  color: var(--text-3);
  background: var(--surface-2);
  text-align: left;
  cursor: pointer;
  transition: background 150ms var(--ease-out);
}

.week-day:hover {
  background: var(--surface-3);
}

.week-day__name {
  grid-column: 1;
  align-self: center;
  font-size: 9px;
  font-weight: 650;
  letter-spacing: 0.08em;
}

.week-day__number {
  grid-column: 1;
  grid-row: 2;
  color: var(--text-2);
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 620;
  letter-spacing: -0.04em;
  line-height: 1;
}

.week-day__month {
  grid-column: 2;
  grid-row: 2;
  align-self: end;
  padding-bottom: 1px;
  font-size: 9px;
}

.week-day__add {
  position: absolute;
  top: 11px;
  right: 11px;
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  border-radius: 6px;
  color: var(--text-3);
  background: var(--surface-1);
  opacity: 0;
  transition: opacity 150ms ease;
}

.week-day:hover .week-day__add {
  opacity: 1;
}

.week-day--today {
  background: var(--accent-faint);
}

.week-day--today .week-day__name,
.week-day--today .week-day__number {
  color: var(--accent-deep);
}

.all-day-row {
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(100px, 1fr));
  border-left: 1px solid var(--stroke);
}

.all-day-label {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 8px 8px 0 0;
  border-right: 1px solid var(--stroke);
  border-bottom: 1px solid var(--stroke);
  color: var(--text-3);
  font-size: 8.5px;
}

.all-day-cell {
  display: flex;
  min-height: 34px;
  flex-direction: column;
  gap: 3px;
  padding: 5px 5px;
  border-right: 1px solid var(--stroke);
  border-bottom: 1px solid var(--stroke);
}

.all-day-event {
  width: 100%;
  padding: 4px 7px;
  overflow: hidden;
  border: 1px solid var(--tone-border);
  border-radius: 6px;
  color: var(--tone);
  background: var(--tone-bg);
  font-size: 9px;
  font-weight: 600;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.week-body {
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(100px, 1fr));
  border-left: 1px solid var(--stroke);
}

.time-gutter {
  position: relative;
  height: var(--total-height);
  border-right: 1px solid var(--stroke);
}

.time-label {
  position: absolute;
  right: 8px;
  transform: translateY(-5px);
  color: var(--text-3);
  font-size: 8.5px;
  font-variant-numeric: tabular-nums;
}

.day-column {
  position: relative;
  height: var(--total-height);
  border-right: 1px solid var(--stroke);
}

.day-column--today {
  background: var(--accent-faint);
}

.hour-line {
  position: absolute;
  right: 0;
  left: 0;
  border-top: 1px solid var(--stroke);
  pointer-events: none;
}

.current-time-line {
  position: absolute;
  right: 0;
  left: 0;
  z-index: 3;
  height: 1px;
  background: var(--accent);
  pointer-events: none;
}

.current-time-line > span {
  position: absolute;
  top: -3px;
  left: -3px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}

.event-block {
  position: absolute;
  z-index: 2;
  display: flex;
  min-height: 24px;
  flex-direction: column;
  gap: 1px;
  padding: 5px 7px;
  overflow: hidden;
  border: 1px solid var(--tone-border);
  border-left: 2px solid var(--tone);
  border-radius: 7px;
  color: var(--text-1);
  background: var(--tone-bg);
  text-align: left;
  cursor: pointer;
  transition: background 150ms var(--ease-out);
}

.event-block:hover {
  z-index: 4;
  background: var(--tone-bg-strong);
}

.event-block--clipped-top {
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
}

.event-block--clipped-bottom {
  border-bottom-left-radius: 2px;
  border-bottom-right-radius: 2px;
}

.event-time {
  overflow: hidden;
  color: var(--tone);
  font-size: 8.5px;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-block strong {
  overflow: hidden;
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1.25;
  text-overflow: ellipsis;
}

.event-location {
  display: flex;
  align-items: center;
  gap: 3px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 8.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-block--compact {
  padding-block: 3px;
}

.event-block--compact .event-time {
  display: none;
}

.column-loading {
  position: absolute;
  inset: 0;
  background: var(--accent-faint);
  animation: pulse-soft 1.4s infinite;
}

.calendar-empty {
  display: flex;
  align-items: center;
  gap: 13px;
  margin: 18px 0 20px;
  padding: 13px 16px;
  border: 1px dashed var(--stroke-strong);
  border-radius: 13px;
  color: var(--text-2);
}

.calendar-empty .empty-state__icon {
  width: 38px;
  height: 38px;
  flex: none;
  border-radius: 12px;
}

.calendar-empty > div {
  flex: 1;
}

.calendar-empty strong {
  font-size: 11.5px;
  font-weight: 600;
}

.calendar-empty p {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 10px;
}

.schedule-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.all-day-switch {
  align-self: flex-start;
}

.footer-delete {
  margin-right: auto;
}

.footer-spacer {
  flex: 1;
}

.form-submit-hidden {
  display: none;
}

.spinner--small {
  width: 13px;
  height: 13px;
  border-width: 1.5px;
}

@media (max-width: 900px) {
  .week-picker {
    order: 2;
  }

  .week-label {
    min-width: 146px;
    font-size: 10px;
  }

  .calendar-card {
    padding-inline: 12px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
