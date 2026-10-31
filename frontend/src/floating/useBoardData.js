import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { diaryApi, ledgerApi, schedulesApi, timetablesApi, todosApi } from '@/api'
import { checkApiHealth } from '@/api/http'
import {
  dateKey,
  dayRangeIso,
  monthRangeIso,
  parseTimeToMinutes,
  weekdayNumber,
} from '@/utils/date'

export function useBoardData() {
  const now = ref(new Date())
  const online = ref(true)
  const loading = ref(true)
  const data = reactive({
    timetable: null,
    todos: null,
    schedules: [],
    ledger: null,
    diary: null,
  })

  let clockTimer = null
  let refreshTimer = null
  let refreshing = false

  const todayKey = computed(() => dateKey(now.value))
  const nowMinutes = computed(
    () =>
      now.value.getHours() * 60 +
      now.value.getMinutes() +
      now.value.getSeconds() / 60,
  )

  const todayCourses = computed(() => {
    if (!data.timetable) return []
    const day = data.timetable.days?.find(
      (item) => item.weekday === weekdayNumber(now.value),
    )
    return [...(day?.courses || [])].sort((a, b) =>
      a.start_time.localeCompare(b.start_time),
    )
  })

  const currentCourse = computed(() =>
    todayCourses.value.find(
      (course) =>
        nowMinutes.value >= parseTimeToMinutes(course.start_time) &&
        nowMinutes.value < parseTimeToMinutes(course.end_time),
    ),
  )

  const nextCourse = computed(() =>
    todayCourses.value.find(
      (course) => parseTimeToMinutes(course.start_time) > nowMinutes.value,
    ),
  )

  const focalSchedule = computed(() => {
    const currentTime = now.value.getTime()
    return (
      data.schedules.find(
        (event) => new Date(event.end_at).getTime() > currentTime,
      ) || null
    )
  })

  const scheduleIsNow = computed(() => {
    if (!focalSchedule.value) return false
    const start = new Date(focalSchedule.value.start_at).getTime()
    const end = new Date(focalSchedule.value.end_at).getTime()
    return start <= now.value.getTime() && end > now.value.getTime()
  })

  const pendingCount = computed(() => data.todos?.total || 0)
  const nextTodo = computed(() => data.todos?.items?.[0] || null)
  const diaryToday = computed(() => {
    const latest = data.diary?.items?.[0]
    return latest?.entry_date === todayKey.value ? latest : null
  })

  async function refresh() {
    if (refreshing) return
    refreshing = true
    try {
      const [healthy, timetableListResult, todosResult, schedulesResult, ledgerResult, diaryResult] =
        await Promise.allSettled([
          checkApiHealth(),
          timetablesApi.list(),
          todosApi.list({
            status: ['pending', 'in_progress'],
            limit: 3,
            sort_by: 'due_at',
            sort_order: 'asc',
          }),
          schedulesApi.list({
            ...dayRangeIso(now.value),
            limit: 20,
            sort_by: 'start_at',
            sort_order: 'asc',
          }),
          ledgerApi.summary(monthRangeIso(now.value)),
          diaryApi.list({ limit: 1, sort_by: 'entry_date', sort_order: 'desc' }),
        ])

      online.value = healthy.status === 'fulfilled' && Boolean(healthy.value)

      if (timetableListResult.status === 'fulfilled') {
        const active = timetableListResult.value.find((item) => item.active)
        if (active) {
          try {
            data.timetable = await timetablesApi.dashboard({
              date: todayKey.value,
              timetableId: active.id,
            })
          } catch {
            data.timetable = null
          }
        } else {
          data.timetable = null
        }
      }

      if (todosResult.status === 'fulfilled') data.todos = todosResult.value
      if (schedulesResult.status === 'fulfilled') {
        data.schedules = schedulesResult.value.items
      }
      if (ledgerResult.status === 'fulfilled') data.ledger = ledgerResult.value
      if (diaryResult.status === 'fulfilled') data.diary = diaryResult.value
    } finally {
      loading.value = false
      refreshing = false
    }
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') refresh()
  }

  onMounted(() => {
    refresh()
    clockTimer = window.setInterval(() => {
      now.value = new Date()
    }, 1000)
    refreshTimer = window.setInterval(refresh, 60000)
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })

  onBeforeUnmount(() => {
    if (clockTimer) window.clearInterval(clockTimer)
    if (refreshTimer) window.clearInterval(refreshTimer)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })

  return {
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
  }
}
