<script setup>
import { GraduationCap, WifiOff } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { timetablesApi } from '@/api'
import { useAppStore } from '@/stores/app'
import {
  WEEKDAYS_CN,
  dateKey,
  formatClock,
  parseTimeToMinutes,
  weekdayNumber,
} from '@/utils/date'

const router = useRouter()
const appStore = useAppStore()

const now = ref(new Date())
const dashboard = ref(null)
const loading = ref(false)
let clockTimer = null
let refreshTimer = null

const coursesToday = computed(() => {
  if (!dashboard.value) return []
  const day = dashboard.value.days?.find(
    (item) => item.weekday === weekdayNumber(now.value),
  )
  return [...(day?.courses || [])].sort((a, b) =>
    a.start_time.localeCompare(b.start_time),
  )
})

const nowMinutes = computed(
  () => now.value.getHours() * 60 + now.value.getMinutes() + now.value.getSeconds() / 60,
)

const currentCourse = computed(() =>
  coursesToday.value.find(
    (course) =>
      nowMinutes.value >= parseTimeToMinutes(course.start_time) &&
      nowMinutes.value < parseTimeToMinutes(course.end_time),
  ),
)

const nextCourse = computed(() =>
  coursesToday.value.find(
    (course) => parseTimeToMinutes(course.start_time) > nowMinutes.value,
  ),
)

const progress = computed(() => {
  const course = currentCourse.value
  if (!course) return 0
  const start = parseTimeToMinutes(course.start_time)
  const end = parseTimeToMinutes(course.end_time)
  return Math.min(100, Math.max(0, ((nowMinutes.value - start) / (end - start)) * 100))
})

const courseLabel = computed(() => {
  if (appStore.backendStatus === 'checking') return '正在连接服务…'
  if (!appStore.backendOnline) return '后端服务离线'
  if (loading.value && !dashboard.value) return '正在读取课表…'
  if (!dashboard.value) return '尚未导入课表'
  if (currentCourse.value) {
    return `正在上课 · ${currentCourse.value.course_name}`
  }
  if (nextCourse.value) {
    return `下一节 ${nextCourse.value.start_time.slice(0, 5)} · ${nextCourse.value.course_name}`
  }
  return coursesToday.value.length ? '今日课程已结束' : '今日无课'
})

const courseTooltip = computed(() => {
  const course = currentCourse.value || nextCourse.value
  if (!course) return '打开课表看板'
  return [
    course.course_name,
    `${course.start_time.slice(0, 5)}–${course.end_time.slice(0, 5)}`,
    course.location,
    course.teacher,
  ]
    .filter(Boolean)
    .join(' · ')
})

const dateLabel = computed(() => {
  const date = now.value
  return `${WEEKDAYS_CN[date.getDay()]} ${String(date.getMonth() + 1).padStart(2, '0')}/${String(
    date.getDate(),
  ).padStart(2, '0')}`
})

async function loadDashboard() {
  if (!appStore.backendOnline) {
    dashboard.value = null
    return
  }
  loading.value = true
  try {
    dashboard.value = await timetablesApi.dashboard({ date: dateKey(now.value) })
  } catch {
    dashboard.value = null
  } finally {
    loading.value = false
  }
}

function handleClockTick() {
  const previousDate = dateKey(now.value)
  now.value = new Date()
  if (dateKey(now.value) !== previousDate) loadDashboard()
}

onMounted(() => {
  loadDashboard()
  clockTimer = window.setInterval(handleClockTick, 1000)
  refreshTimer = window.setInterval(loadDashboard, 120000)
})

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer)
  if (refreshTimer) window.clearInterval(refreshTimer)
})

watch(() => appStore.timetableVersion, loadDashboard)
watch(
  () => appStore.backendOnline,
  (online) => {
    if (online) loadDashboard()
  },
)
</script>

<template>
  <button
    class="now-island"
    :class="{ 'now-island--live': currentCourse }"
    :title="courseTooltip"
    type="button"
    @click="router.push('/timetable')"
  >
    <span class="island-date">{{ dateLabel }}</span>
    <span class="island-divider"></span>
    <span class="island-clock mono">{{ formatClock(now) }}</span>
    <span class="island-divider"></span>
    <span class="island-course" :class="{ 'island-course--muted': !currentCourse }">
      <WifiOff v-if="!appStore.backendOnline" :size="13" />
      <GraduationCap v-else :size="14" />
      <span class="island-course__text">{{ courseLabel }}</span>
    </span>
    <span
      v-if="currentCourse"
      class="island-progress"
      :style="{ width: `${progress}%` }"
    ></span>
  </button>
</template>

<style scoped>
.now-island {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  height: 34px;
  max-width: min(560px, 44vw);
  padding: 0 14px;
  overflow: hidden;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-2);
  background: var(--surface-1);
  box-shadow: var(--shadow-sm);
  font-size: 11.5px;
  white-space: nowrap;
  cursor: pointer;
  transition:
    border-color 180ms var(--ease-out),
    background 180ms var(--ease-out),
    transform 180ms var(--ease-out);
}

.now-island:hover {
  border-color: var(--stroke-strong);
  background: var(--surface-2);
}

.now-island:active {
  transform: scale(0.995);
}

.now-island--live {
  border-color: var(--stroke-accent);
  background: var(--accent-faint);
  box-shadow: var(--shadow-sm);
}

.island-date {
  color: var(--text-3);
  font-weight: 560;
}

.island-clock {
  color: var(--text-1);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.island-divider {
  width: 1px;
  height: 12px;
  background: var(--stroke-strong);
}

.island-course {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  color: var(--accent-deep);
  font-weight: 580;
}

.island-course--muted {
  color: var(--text-3);
  font-weight: 520;
}

.island-course__text {
  overflow: hidden;
  text-overflow: ellipsis;
}

.island-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
  transition: width 1s linear;
}

@media (max-width: 1160px) {
  .island-date,
  .now-island .island-divider:first-of-type {
    display: none;
  }
}

@media (max-width: 920px) {
  .now-island {
    max-width: 330px;
  }

  .island-divider:last-of-type {
    display: none;
  }
}
</style>
