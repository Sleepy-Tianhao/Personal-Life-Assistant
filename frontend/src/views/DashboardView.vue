<script setup>
import {
  ArrowUpRight,
  BookOpen,
  Check,
  CircleDollarSign,
  Clock3,
  GraduationCap,
  ListTodo,
  NotebookPen,
  Plus,
  Sparkles,
  Wallet,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { diaryApi, ledgerApi, schedulesApi, timetablesApi, todosApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import MetricCard from '@/components/MetricCard.vue'
import { useToastStore } from '@/stores/toast'
import {
  WEEKDAYS_CN,
  dateKey,
  dayRangeIso,
  formatDateLong,
  formatDueDate,
  formatTime,
  getGreeting,
  monthRangeIso,
  parseTimeToMinutes,
  relativeTimeLabel,
  weekdayNumber,
} from '@/utils/date'
import { toneFor, toneStyle } from '@/utils/colors'
import { formatMoney } from '@/utils/money'

const router = useRouter()
const toast = useToastStore()

const loading = ref(true)
const pendingTasks = ref([])
const pendingTotal = ref(0)
const ledger = ref(null)
const timetable = ref(null)
const schedules = ref([])
const latestDiary = ref(null)
const diaryTotal = ref(0)
const completingId = ref(null)

const now = new Date()
const greeting = getGreeting(now)
const today = new Date()

const todayCourses = computed(() => {
  if (!timetable.value) return []
  const day = timetable.value.days?.find((item) => item.weekday === weekdayNumber(today))
  return [...(day?.courses || [])].sort((a, b) =>
    a.start_time.localeCompare(b.start_time),
  )
})

const nowMinutes = now.getHours() * 60 + now.getMinutes()
const nextCourse = computed(() =>
  todayCourses.value.find(
    (course) => parseTimeToMinutes(course.start_time) > nowMinutes,
  ),
)

const timeline = computed(() => {
  const courseItems = todayCourses.value.map((course) => ({
    id: `course-${course.id}`,
    kind: 'course',
    start: parseTimeToMinutes(course.start_time),
    end: parseTimeToMinutes(course.end_time),
    time: `${course.start_time.slice(0, 5)} – ${course.end_time.slice(0, 5)}`,
    title: course.course_name,
    subtitle: [course.location, course.teacher].filter(Boolean).join(' · '),
    tag: course.course_code,
    tone: toneFor(course.course_code),
  }))

  const scheduleItems = schedules.value.map((schedule) => {
    const start = new Date(schedule.start_at)
    const end = new Date(schedule.end_at)
    return {
      id: `schedule-${schedule.id}`,
      kind: 'schedule',
      start: start.getHours() * 60 + start.getMinutes(),
      end: end.getHours() * 60 + end.getMinutes(),
      time: `${formatTime(start)} – ${formatTime(end)}`,
      title: schedule.title,
      subtitle: schedule.location || schedule.description || '日程安排',
      tag: schedule.all_day ? '全天' : '日程',
      tone: toneFor(schedule.title),
    }
  })

  return [...courseItems, ...scheduleItems].sort((a, b) => a.start - b.start)
})

const summaryLine = computed(() => {
  if (loading.value) return '正在同步你的生活数据…'
  const parts = []
  if (todayCourses.value.length) parts.push(`今天有 ${todayCourses.value.length} 节课`)
  if (pendingTotal.value) parts.push(`${pendingTotal.value} 件待办等你处理`)
  if (schedules.value.length) parts.push(`${schedules.value.length} 个日程`)
  if (!parts.length) return '今天没有安排，给自己留一点呼吸的空间。'
  return `${parts.join('，')}。`
})

const nextCourseHint = computed(() => {
  if (!nextCourse.value) {
    return todayCourses.value.length ? '今日课程已结束' : '今日没有课程'
  }
  return `${nextCourse.value.start_time.slice(0, 5)} ${nextCourse.value.course_name}`
})

const ledgerHint = computed(() => {
  if (!ledger.value) return '本月暂无记录'
  return `收入 ${formatMoney(ledger.value.income_cents)}`
})

async function loadDashboard() {
  loading.value = true
  const [todoResult, ledgerResult, timetableResult, scheduleResult, diaryResult] =
    await Promise.allSettled([
      todosApi.list({
        status: ['pending', 'in_progress'],
        limit: 5,
        sort_by: 'due_at',
        sort_order: 'asc',
      }),
      ledgerApi.summary({
        ...monthRangeIso(today),
        group_by: 'category',
      }),
      timetablesApi.dashboard({ date: dateKey(today) }),
      schedulesApi.list({
        ...dayRangeIso(today),
        limit: 50,
        sort_by: 'start_at',
        sort_order: 'asc',
      }),
      diaryApi.list({ limit: 1, sort_by: 'entry_date', sort_order: 'desc' }),
    ])

  if (todoResult.status === 'fulfilled') {
    pendingTasks.value = todoResult.value.items
    pendingTotal.value = todoResult.value.total
  }
  if (ledgerResult.status === 'fulfilled') ledger.value = ledgerResult.value
  if (timetableResult.status === 'fulfilled') timetable.value = timetableResult.value
  else timetable.value = null
  if (scheduleResult.status === 'fulfilled') schedules.value = scheduleResult.value.items
  if (diaryResult.status === 'fulfilled') {
    latestDiary.value = diaryResult.value.items[0] || null
    diaryTotal.value = diaryResult.value.total
  }

  loading.value = false
}

async function completeTask(task) {
  if (completingId.value) return
  completingId.value = task.id
  try {
    await todosApi.update(task.id, { status: 'completed' })
    toast.success('完成一件待办')
    await loadDashboard()
  } catch (error) {
    toast.error(error.message)
  } finally {
    completingId.value = null
  }
}

function open(path) {
  router.push(path)
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page">
    <div class="page-inner dashboard-page">
      <section class="hero card">
        <div class="hero-noise"></div>
        <div class="hero-orbit hero-orbit--one"></div>
        <div class="hero-orbit hero-orbit--two"></div>

        <div class="hero-copy">
          <div class="hero-date">
            <span class="hero-date__dot"></span>
            {{ formatDateLong(today) }}
          </div>
          <h1>
            {{ greeting }}，
            <span>把今天过得具体一点。</span>
          </h1>
          <p>{{ summaryLine }}</p>

          <div class="quick-actions">
            <button class="quick-action" type="button" @click="open('/todos')">
              <ListTodo :size="16" />
              添加待办
            </button>
            <button class="quick-action" type="button" @click="open('/ledger')">
              <CircleDollarSign :size="16" />
              记一笔
            </button>
            <button class="quick-action" type="button" @click="open('/diary')">
              <NotebookPen :size="16" />
              写日记
            </button>
          </div>
        </div>

        <div class="hero-side">
          <div class="date-sculpture">
            <span class="date-sculpture__weekday">{{ WEEKDAYS_CN[today.getDay()] }}</span>
            <strong>{{ String(today.getDate()).padStart(2, '0') }}</strong>
            <span class="date-sculpture__month">{{ today.getMonth() + 1 }}月 · {{ today.getFullYear() }}</span>
          </div>
          <div class="hero-mini-stats">
            <div>
              <span>课程</span>
              <strong>{{ todayCourses.length }}</strong>
            </div>
            <div>
              <span>日程</span>
              <strong>{{ schedules.length }}</strong>
            </div>
            <div>
              <span>待办</span>
              <strong>{{ pendingTotal }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="metrics-grid">
        <MetricCard
          label="今日课程"
          :value="loading ? '—' : todayCourses.length"
          :hint="nextCourseHint"
          :icon="GraduationCap"
          tone="accent"
        />
        <MetricCard
          label="待办事项"
          :value="loading ? '—' : pendingTotal"
          :hint="pendingTasks.length ? '优先处理最紧急的事项' : '清单很干净'"
          :icon="ListTodo"
          tone="warning"
        />
        <MetricCard
          label="本月支出"
          :value="loading ? '—' : formatMoney(ledger?.expense_cents || 0)"
          :hint="ledgerHint"
          :icon="Wallet"
          tone="expense"
        />
        <MetricCard
          label="日记累计"
          :value="loading ? '—' : diaryTotal"
          :hint="latestDiary ? `上次记录于 ${latestDiary.entry_date}` : '写下第一篇日记吧'"
          :icon="BookOpen"
          tone="income"
        />
      </section>

      <section class="dashboard-grid">
        <article class="card timeline-card">
          <header class="card-head">
            <div>
              <span class="eyebrow">TODAY'S FLOW</span>
              <h2 class="section-title">
                <Clock3 :size="17" />
                今日时间轴
              </h2>
            </div>
            <RouterLink to="/schedule" class="link">查看日程 <ArrowUpRight :size="13" /></RouterLink>
          </header>

          <div v-if="loading" class="loading-state">
            <span class="spinner"></span>
            正在整理今天的安排
          </div>
          <div v-else-if="!timeline.length" class="empty-state">
            <span class="empty-state__icon"><Sparkles :size="20" /></span>
            <strong>今天还没有安排</strong>
            <p>留白也很好，或者为今天安排一件期待的小事。</p>
            <button class="btn btn-sm" type="button" @click="open('/schedule')">
              <Plus :size="14" /> 添加日程
            </button>
          </div>
          <div v-else class="timeline">
            <div class="timeline-line"></div>
            <div
              v-for="item in timeline"
              :key="item.id"
              class="timeline-item"
              :class="{ 'timeline-item--course': item.kind === 'course' }"
              :style="toneStyle(item.title)"
            >
              <div class="timeline-time mono">{{ item.time }}</div>
              <div class="timeline-track">
                <span class="timeline-dot"></span>
              </div>
              <div class="timeline-content">
                <div class="timeline-heading">
                  <strong>{{ item.title }}</strong>
                  <span class="timeline-tag">{{ item.tag }}</span>
                </div>
                <p v-if="item.subtitle">{{ item.subtitle }}</p>
              </div>
            </div>
          </div>
        </article>

        <div class="dashboard-side">
          <article class="card focus-card">
            <header class="card-head card-head--compact">
              <div>
                <span class="eyebrow">FOCUS</span>
                <h2 class="section-title">
                  <ListTodo :size="17" />
                  待办焦点
                </h2>
              </div>
              <RouterLink to="/todos" class="link">全部 <ArrowUpRight :size="13" /></RouterLink>
            </header>

            <div v-if="loading" class="loading-state loading-state--small">
              <span class="spinner"></span>
            </div>
            <EmptyState
              v-else-if="!pendingTasks.length"
              title="待办已清空"
              description="享受一下没有悬而未决事项的轻松感。"
              :icon="Check"
            />
            <ul v-else class="focus-list">
              <li v-for="task in pendingTasks" :key="task.id" class="focus-item">
                <button
                  class="focus-check"
                  type="button"
                  :disabled="completingId === task.id"
                  @click="completeTask(task)"
                >
                  <Check :size="12" />
                </button>
                <div class="focus-copy">
                  <span class="focus-title">{{ task.title }}</span>
                  <span class="focus-meta">
                    <span
                      class="priority-dot"
                      :class="`priority-dot--${task.priority}`"
                    ></span>
                    {{ task.due_at ? formatDueDate(task.due_at) : '未设置截止时间' }}
                  </span>
                </div>
              </li>
            </ul>
          </article>

          <article class="card finance-card">
            <header class="card-head card-head--compact">
              <div>
                <span class="eyebrow">MONTHLY</span>
                <h2 class="section-title">
                  <Wallet :size="17" />
                  本月收支
                </h2>
              </div>
              <RouterLink to="/ledger" class="link">账本 <ArrowUpRight :size="13" /></RouterLink>
            </header>

            <div class="finance-balance">
              <span>结余</span>
              <strong class="money">{{ formatMoney(ledger?.balance_cents || 0) }}</strong>
            </div>
            <div class="finance-split">
              <div>
                <span class="finance-dot finance-dot--income"></span>
                <span>收入</span>
                <strong>{{ formatMoney(ledger?.income_cents || 0) }}</strong>
              </div>
              <div>
                <span class="finance-dot finance-dot--expense"></span>
                <span>支出</span>
                <strong>{{ formatMoney(ledger?.expense_cents || 0) }}</strong>
              </div>
            </div>
            <div class="finance-bar">
              <span
                class="finance-bar__income"
                :style="{
                  width: `${
                    ledger?.income_cents
                      ? (ledger.income_cents /
                          Math.max(
                            ledger.income_cents + ledger.expense_cents,
                            1,
                          )) *
                        100
                      : 0
                  }%`,
                }"
              ></span>
            </div>
          </article>

          <article v-if="latestDiary" class="mini-diary card" @click="open('/diary')">
            <div class="mini-diary__icon"><BookOpen :size="17" /></div>
            <div class="mini-diary__copy">
              <span class="eyebrow">RECENT NOTE</span>
              <strong>{{ latestDiary.title || '无题日记' }}</strong>
              <p>{{ latestDiary.content.slice(0, 70) }}{{ latestDiary.content.length > 70 ? '…' : '' }}</p>
            </div>
            <span class="mini-diary__time">{{ relativeTimeLabel(latestDiary.created_at) }}</span>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding-top: 4px;
}

.hero {
  position: relative;
  display: flex;
  min-height: 232px;
  align-items: stretch;
  justify-content: space-between;
  overflow: hidden;
  border-color: #d7e9de;
  background: #e9f4ed;
  box-shadow: none;
}

.hero-noise {
  display: none;
}

.hero-orbit {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.hero-orbit--one {
  top: -180px;
  right: -52px;
  width: 470px;
  height: 470px;
  background: #deeee4;
}

.hero-orbit--two {
  top: -92px;
  right: 36px;
  width: 290px;
  height: 290px;
  border: 1px solid #d0e5d8;
}

.hero-copy {
  position: relative;
  z-index: 1;
  display: flex;
  max-width: 710px;
  flex-direction: column;
  justify-content: center;
  padding: 34px 38px;
}

.hero-date {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-2);
  font-size: 11.5px;
  font-weight: 580;
  letter-spacing: 0.02em;
}

.hero-date__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.hero h1 {
  max-width: 680px;
  margin-top: 16px;
  font-family: var(--font-display);
  font-size: clamp(30px, 3.1vw, 46px);
  font-weight: 690;
  letter-spacing: -0.045em;
  line-height: 1.15;
}

.hero h1 span {
  color: var(--text-2);
  font-weight: 460;
}

.hero p {
  max-width: 560px;
  margin-top: 12px;
  color: var(--text-2);
  font-size: 13px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}

.quick-action {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 12px;
  border: 1px solid #cfe3d6;
  border-radius: 10px;
  color: var(--text-2);
  background: #ffffff;
  font-size: 11.5px;
  font-weight: 570;
  cursor: pointer;
  transition: 160ms var(--ease-out);
}

.quick-action:hover {
  border-color: var(--accent-deep);
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.hero-side {
  position: relative;
  z-index: 1;
  display: flex;
  width: 300px;
  flex: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 28px 38px 28px 0;
}

.date-sculpture {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 168px;
  padding: 14px 12px 16px;
  border: 1px solid #cfe3d6;
  border-radius: 30px;
  background: #ffffff;
}

.date-sculpture__weekday {
  color: var(--text-3);
  font-size: 10px;
  font-weight: 660;
  letter-spacing: 0.16em;
}

.date-sculpture strong {
  font-family: var(--font-display);
  font-size: 68px;
  font-weight: 610;
  letter-spacing: -0.08em;
  line-height: 0.96;
}

.date-sculpture__month {
  margin-top: 9px;
  color: var(--text-2);
  font-size: 10.5px;
}

.hero-mini-stats {
  display: flex;
  gap: 8px;
}

.hero-mini-stats div {
  display: flex;
  min-width: 62px;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 7px 9px;
  border: 1px solid #cfe3d6;
  border-radius: 10px;
  background: #f6fbf8;
}

.hero-mini-stats span {
  color: var(--text-3);
  font-size: 9.5px;
}

.hero-mini-stats strong {
  font-size: 15px;
  font-weight: 620;
  font-variant-numeric: tabular-nums;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.75fr);
  gap: 14px;
  margin-top: 14px;
}

.timeline-card {
  min-height: 420px;
  padding: 20px 22px 22px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.card-head .section-title {
  margin-top: 5px;
}

.card-head .link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding-top: 3px;
}

.card-head--compact {
  margin-bottom: 12px;
}

.timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.timeline-line {
  position: absolute;
  top: 17px;
  bottom: 17px;
  left: 114px;
  width: 1px;
  background: var(--stroke);
}

.timeline-item {
  display: grid;
  grid-template-columns: 90px 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 9px 8px 9px 0;
  border-radius: 12px;
  transition: background 160ms var(--ease-out);
}

.timeline-item:hover {
  background: var(--surface-2);
}

.timeline-time {
  padding-top: 5px;
  color: var(--text-3);
  font-size: 10.5px;
  text-align: right;
  white-space: nowrap;
}

.timeline-track {
  position: relative;
  display: flex;
  height: 100%;
  justify-content: center;
  padding-top: 7px;
}

.timeline-dot {
  position: relative;
  z-index: 1;
  width: 9px;
  height: 9px;
  border: 2px solid var(--surface-1);
  border-radius: 50%;
  background: var(--tone, var(--accent));
}

.timeline-content {
  min-width: 0;
  padding: 4px 11px 5px;
  border: 1px solid var(--tone-border, var(--stroke));
  border-radius: 11px;
  background: var(--tone-bg, var(--accent-faint));
}

.timeline-heading {
  display: flex;
  align-items: center;
  gap: 9px;
}

.timeline-heading strong {
  overflow: hidden;
  color: var(--text-1);
  font-size: 13px;
  font-weight: 610;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-tag {
  padding: 1px 6px;
  border-radius: 5px;
  color: var(--tone, var(--accent));
  background: var(--tone-bg, var(--accent-soft));
  font-size: 9px;
  font-weight: 650;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.timeline-content p {
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 10.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-side {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 14px;
}

.focus-card,
.finance-card {
  padding: 18px 20px;
}

.focus-list {
  display: flex;
  flex-direction: column;
}

.focus-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--stroke);
}

.focus-item:last-child {
  padding-bottom: 2px;
  border-bottom: 0;
}

.focus-check {
  display: grid;
  width: 19px;
  height: 19px;
  flex: none;
  margin-top: 1px;
  place-items: center;
  border: 1px solid var(--stroke-strong);
  border-radius: 6px;
  color: transparent;
  background: var(--surface-1);
  cursor: pointer;
  transition: 160ms var(--ease-out);
}

.focus-check:hover {
  border-color: var(--accent-deep);
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.focus-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.focus-title {
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 560;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  color: var(--text-3);
  font-size: 9.5px;
}

.priority-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-3);
}

.priority-dot--high {
  background: var(--danger);
}

.priority-dot--medium {
  background: var(--warning);
}

.priority-dot--low {
  background: var(--success);
}

.finance-balance {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 7px 0 11px;
}

.finance-balance span {
  color: var(--text-3);
  font-size: 10.5px;
}

.finance-balance strong {
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 650;
  letter-spacing: -0.04em;
}

.finance-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.finance-split div {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 6px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid var(--stroke);
  border-radius: 10px;
  background: var(--surface-2);
}

.finance-split span:not(.finance-dot) {
  color: var(--text-3);
  font-size: 9.5px;
}

.finance-split strong {
  grid-column: 2;
  font-size: 11.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.finance-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.finance-dot--income {
  background: var(--income);
}

.finance-dot--expense {
  background: var(--expense);
}

.finance-bar {
  position: relative;
  height: 4px;
  margin-top: 13px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--expense);
}

.finance-bar__income {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--income);
  transition: width 500ms var(--ease-out);
}

.mini-diary {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 14px 16px;
  cursor: pointer;
  transition:
    border-color 160ms var(--ease-out),
    transform 160ms var(--ease-out);
}

.mini-diary:hover {
  border-color: var(--accent-deep);
}

.mini-diary__icon {
  display: grid;
  width: 32px;
  height: 32px;
  flex: none;
  place-items: center;
  border-radius: 10px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.mini-diary__copy {
  min-width: 0;
  flex: 1;
}

.mini-diary__copy strong {
  display: block;
  margin-top: 1px;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-diary__copy p {
  display: -webkit-box;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 10.5px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mini-diary__time {
  flex: none;
  color: var(--text-3);
  font-size: 9px;
}

.loading-state--small {
  min-height: 90px;
}

@media (max-width: 1220px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-grid {
    grid-template-columns: minmax(0, 1.25fr) minmax(300px, 0.75fr);
  }

  .hero-side {
    width: 250px;
    padding-right: 26px;
  }
}

@media (max-width: 980px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .hero-side {
    display: none;
  }
}

@media (max-width: 680px) {
  .hero-copy {
    padding: 26px 22px;
  }

  .metrics-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
