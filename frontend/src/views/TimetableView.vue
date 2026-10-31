<script setup>
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FileUp,
  GraduationCap,
  MapPin,
  Settings2,
  Trash2,
  Upload,
  User,
  X,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { timetablesApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useAppStore } from '@/stores/app'
import { useDialogStore } from '@/stores/dialog'
import { useToastStore } from '@/stores/toast'
import { toneFor, toneStyle } from '@/utils/colors'
import {
  WEEKDAYS_MONDAY_FIRST,
  addDays,
  dateKey,
  parseDateKey,
  parseTimeToMinutes,
  startOfWeek,
  weekdayNumber,
} from '@/utils/date'

const toast = useToastStore()
const dialog = useDialogStore()
const appStore = useAppStore()

const timetables = ref([])
const selectedId = ref(null)
const dashboard = ref(null)
const loading = ref(true)
const weekDate = ref(new Date())
const importOpen = ref(false)
const importing = ref(false)
const editOpen = ref(false)
const savingMeta = ref(false)
const fileInput = ref(null)
const selectedFile = ref(null)
const dragging = ref(false)
const lastWarnings = ref([])
const detailCourse = ref(null)
const now = ref(new Date())

const importForm = reactive({
  name: '',
  semesterStartDate: '',
  setActive: true,
})

const metaForm = reactive({
  name: '',
  semesterStartDate: '',
})

const selectedTimetable = computed(
  () => timetables.value.find((item) => item.id === selectedId.value) || null,
)

const days = computed(() => dashboard.value?.days || [])
const allCourses = computed(() => days.value.flatMap((day) => day.courses))
const todayKey = computed(() => dateKey(now.value))

const startHour = computed(() => {
  if (!allCourses.value.length) return 8
  const earliest = Math.min(
    ...allCourses.value.map((course) => parseTimeToMinutes(course.start_time)),
  )
  return Math.max(0, Math.min(8, Math.floor(earliest / 60)))
})

const endHour = computed(() => {
  if (!allCourses.value.length) return 18
  const latest = Math.max(
    ...allCourses.value.map((course) => parseTimeToMinutes(course.end_time)),
  )
  return Math.min(24, Math.max(18, Math.ceil(latest / 60)))
})

const hourHeight = 62
const hours = computed(() =>
  Array.from(
    { length: Math.max(1, endHour.value - startHour.value) },
    (_, index) => startHour.value + index,
  ),
)

const gridStyle = computed(() => ({
  '--tt-hour-height': `${hourHeight}px`,
  '--tt-height': `${(endHour.value - startHour.value) * hourHeight}px`,
}))

const currentWeekLabel = computed(() => {
  if (!dashboard.value) return ''
  if (dashboard.value.current_week === null) return '周次未启用'
  if (dashboard.value.current_week === 0) return '学期未开始'
  return `第 ${dashboard.value.current_week} 周`
})

const weekRangeLabel = computed(() => {
  if (!dashboard.value) return ''
  const start = parseDateKey(dashboard.value.week_start_date)
  const end = parseDateKey(dashboard.value.week_end_date)
  if (!start || !end) return ''
  return `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日 – ${
    end.getMonth() + 1
  }月${end.getDate()}日`
})

const nowMinutes = computed(
  () => now.value.getHours() * 60 + now.value.getMinutes() + now.value.getSeconds() / 60,
)

const currentCourseKey = computed(() => {
  if (!dashboard.value) return null
  const day = days.value.find((item) => item.date === todayKey.value)
  if (!day) return null
  const course = day.courses.find(
    (item) =>
      nowMinutes.value >= parseTimeToMinutes(item.start_time) &&
      nowMinutes.value < parseTimeToMinutes(item.end_time),
  )
  return course ? `course-${course.id}` : null
})

const currentLineTop = computed(() => {
  const minutes = nowMinutes.value
  if (minutes < startHour.value * 60 || minutes > endHour.value * 60) return null
  return ((minutes - startHour.value * 60) / 60) * hourHeight
})

const showCurrentLine = computed(
  () => Boolean(dashboard.value) && days.value.some((day) => day.date === todayKey.value),
)

const emptyWeek = computed(
  () =>
    Boolean(dashboard.value) &&
    days.value.length > 0 &&
    allCourses.value.length === 0,
)

function courseStyle(course) {
  const start = parseTimeToMinutes(course.start_time)
  const end = parseTimeToMinutes(course.end_time)
  const clampedStart = Math.max(start, startHour.value * 60)
  const clampedEnd = Math.min(end, endHour.value * 60)
  return {
    ...toneStyle(course.course_code),
    top: `${((clampedStart - startHour.value * 60) / 60) * hourHeight}px`,
    height: `${Math.max(28, ((clampedEnd - clampedStart) / 60) * hourHeight)}px`,
  }
}

function isCourseNow(course) {
  return currentCourseKey.value === `course-${course.id}`
}

function dayCourses(day) {
  return day.courses || []
}

async function loadTimetables({ preferredId = null, refreshDashboard = true } = {}) {
  loading.value = true
  try {
    const list = await timetablesApi.list()
    timetables.value = list
    const preferred =
      preferredId ??
      (selectedId.value && list.some((item) => item.id === selectedId.value)
        ? selectedId.value
        : list.find((item) => item.active)?.id ?? list[0]?.id ?? null)
    selectedId.value = preferred
    if (!preferred) {
      dashboard.value = null
      return
    }
    if (refreshDashboard) await loadDashboard()
  } catch (error) {
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

async function loadDashboard() {
  if (!selectedId.value) {
    dashboard.value = null
    return
  }
  loading.value = true
  try {
    dashboard.value = await timetablesApi.dashboard({
      date: dateKey(weekDate.value),
      timetableId: selectedId.value,
    })
  } catch (error) {
    dashboard.value = null
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

async function selectTimetable() {
  lastWarnings.value = []
  weekDate.value = startOfWeek(new Date())
  await loadDashboard()
}

async function moveWeek(offset) {
  weekDate.value = addDays(weekDate.value, offset * 7)
  await loadDashboard()
}

async function goThisWeek() {
  weekDate.value = startOfWeek(new Date())
  await loadDashboard()
}

function openImport() {
  selectedFile.value = null
  importForm.name = ''
  importForm.semesterStartDate = dateKey(startOfWeek(new Date()))
  importForm.setActive = true
  if (fileInput.value) fileInput.value.value = ''
  importOpen.value = true
}

function chooseFile() {
  fileInput.value?.click()
}

function acceptFile(file) {
  if (!file) return
  const suffix = file.name.split('.').pop()?.toLowerCase()
  if (!['html', 'htm'].includes(suffix)) {
    toast.warning('请选择 .html 或 .htm 格式的课表文件')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    toast.warning('课表文件不能超过 2 MB')
    return
  }
  selectedFile.value = file
  importForm.name = file.name.replace(/\.(html?|HTML?)$/, '')
}

function onFileChange(event) {
  acceptFile(event.target.files?.[0])
}

function onDrop(event) {
  dragging.value = false
  acceptFile(event.dataTransfer?.files?.[0])
}

async function submitImport() {
  if (!selectedFile.value) {
    toast.warning('请先选择课表 HTML 文件')
    return
  }
  importing.value = true
  try {
    const result = await timetablesApi.import(selectedFile.value, {
      name: importForm.name.trim() || undefined,
      semesterStartDate: importForm.semesterStartDate || undefined,
      setActive: importForm.setActive,
    })
    lastWarnings.value = result.warnings || []
    importOpen.value = false
    toast.success(
      `课表已导入，共 ${result.timetable.session_count} 个课程节次`,
    )
    if (result.warnings?.length) {
      toast.warning(`导入完成，有 ${result.warnings.length} 条解析警告`)
    }
    appStore.markTimetableChanged()
    weekDate.value = startOfWeek(new Date())
    await loadTimetables({ preferredId: result.timetable.id })
  } catch (error) {
    toast.error(error.message)
  } finally {
    importing.value = false
  }
}

async function activateSelected() {
  if (!selectedId.value) return
  try {
    await timetablesApi.activate(selectedId.value)
    toast.success('已设为当前课表')
    appStore.markTimetableChanged()
    await loadTimetables({ preferredId: selectedId.value })
  } catch (error) {
    toast.error(error.message)
  }
}

function openEdit() {
  if (!selectedTimetable.value) return
  metaForm.name = selectedTimetable.value.name
  metaForm.semesterStartDate = selectedTimetable.value.semester_start_date || ''
  editOpen.value = true
}

async function saveMeta() {
  if (!metaForm.name.trim()) {
    toast.warning('课表名称不能为空')
    return
  }
  savingMeta.value = true
  try {
    await timetablesApi.update(selectedId.value, {
      name: metaForm.name.trim(),
      semester_start_date: metaForm.semesterStartDate || null,
    })
    toast.success('课表信息已更新')
    editOpen.value = false
    appStore.markTimetableChanged()
    await loadTimetables({ preferredId: selectedId.value })
  } catch (error) {
    toast.error(error.message)
  } finally {
    savingMeta.value = false
  }
}

async function deleteSelected() {
  if (!selectedTimetable.value) return
  const confirmed = await dialog.ask({
    title: '删除课表',
    message: `确定删除「${selectedTimetable.value.name}」及其全部课程吗？`,
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  try {
    await timetablesApi.remove(selectedId.value)
    toast.success('课表已删除')
    editOpen.value = false
    selectedId.value = null
    appStore.markTimetableChanged()
    await loadTimetables()
  } catch (error) {
    toast.error(error.message)
  }
}

let clockTimer = null
onMounted(() => {
  loadTimetables()
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 30000)
})

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <PageHeader
        eyebrow="TIMETABLE"
        title="课表看板"
        description="把 HTML 课表变成清晰的一周视图，当前课程、教室和周次一目了然。"
      >
        <template #actions>
          <button class="btn" type="button" :disabled="!selectedTimetable" @click="openEdit">
            <Settings2 :size="15" />
            学期设置
          </button>
          <button class="btn btn-primary" type="button" @click="openImport">
            <Upload :size="15" />
            导入课表
          </button>
        </template>
      </PageHeader>

      <div v-if="lastWarnings.length" class="warning-banner">
        <div>
          <strong>课表已导入，但有 {{ lastWarnings.length }} 条解析警告</strong>
          <p v-for="warning in lastWarnings.slice(0, 3)" :key="warning">{{ warning }}</p>
          <p v-if="lastWarnings.length > 3" class="subtle">
            还有 {{ lastWarnings.length - 3 }} 条警告…
          </p>
        </div>
        <button class="icon-btn" type="button" @click="lastWarnings = []">
          <X :size="15" />
        </button>
      </div>

      <div v-if="loading && !timetables.length" class="loading-state timetable-loading">
        <span class="spinner"></span>
        正在加载课表
      </div>

      <section v-else-if="!timetables.length" class="empty-timetable card">
        <div class="empty-timetable__visual">
          <span class="orb orb--one"></span>
          <span class="orb orb--two"></span>
          <span class="empty-icon"><GraduationCap :size="34" :stroke-width="1.4" /></span>
        </div>
        <div class="empty-timetable__copy">
          <span class="eyebrow">IMPORT YOUR SEMESTER</span>
          <h2>从 HTML 课表开始</h2>
          <p>
            导入教务系统导出的 HTML 文件，自动识别课程代码、名称、教师、地点和周次范围。
            课表只保存在你本地的 SQLite 数据库中。
          </p>
          <button class="btn btn-primary" type="button" @click="openImport">
            <FileUp :size="15" />
            选择 HTML 文件
          </button>
        </div>
      </section>

      <template v-else>
        <section class="timetable-toolbar card">
          <div class="toolbar-select">
            <span class="toolbar-label">查看课表</span>
            <select
              v-model="selectedId"
              class="select timetable-select"
              @change="selectTimetable"
            >
              <option v-for="item in timetables" :key="item.id" :value="item.id">
                {{ item.name }}{{ item.active ? ' · 当前' : '' }}
              </option>
            </select>
          </div>

          <div class="toolbar-meta">
            <span v-if="selectedTimetable?.active" class="chip chip--success">
              <span class="dot"></span>
              当前激活
            </span>
            <button
              v-else
              class="btn btn-sm"
              type="button"
              @click="activateSelected"
            >
              设为当前
            </button>
            <span class="chip">{{ selectedTimetable?.session_count || 0 }} 节课程</span>
            <span class="chip chip--accent">{{ currentWeekLabel }}</span>
          </div>

          <div class="week-nav">
            <button class="icon-btn" type="button" title="上一周" @click="moveWeek(-1)">
              <ChevronLeft :size="16" />
            </button>
            <button class="week-nav__label" type="button" @click="goThisWeek">
              {{ weekRangeLabel }}
            </button>
            <button class="icon-btn" type="button" title="下一周" @click="moveWeek(1)">
              <ChevronRight :size="16" />
            </button>
          </div>
        </section>

        <section class="timetable-card card" :style="gridStyle">
          <header class="timetable-head">
            <div>
              <span class="eyebrow">WEEK BOARD</span>
              <h2 class="section-title">
                <GraduationCap :size="17" />
                {{ selectedTimetable?.name }}
              </h2>
            </div>
            <div class="head-meta">
              <span v-if="selectedTimetable?.semester_start_date" class="subtle">
                学期起点 {{ selectedTimetable.semester_start_date }}
              </span>
              <span v-else class="chip chip--warning">未设置学期开始日期</span>
            </div>
          </header>

          <div class="timetable-scroll">
            <div class="timetable-frame">
              <div class="tt-header">
                <div class="tt-gutter"></div>
                <div
                  v-for="day in days"
                  :key="day.date"
                  class="tt-day-head"
                  :class="{ 'tt-day-head--today': day.date === todayKey }"
                >
                  <span class="tt-day-name">{{ WEEKDAYS_MONDAY_FIRST[day.weekday - 1] }}</span>
                  <strong>{{ parseDateKey(day.date)?.getDate() }}</strong>
                  <span class="tt-day-date">{{ day.date.slice(5).replace('-', '/') }}</span>
                </div>
              </div>

              <div class="tt-body">
                <div class="tt-gutter tt-times">
                  <span
                    v-for="hour in hours"
                    :key="hour"
                    class="tt-time"
                    :style="{ top: `${(hour - startHour) * hourHeight}px` }"
                  >
                    {{ String(hour).padStart(2, '0') }}:00
                  </span>
                </div>

                <div
                  v-for="day in days"
                  :key="day.date"
                  class="tt-day-column"
                  :class="{ 'tt-day-column--today': day.date === todayKey }"
                >
                  <span
                    v-for="hour in hours"
                    :key="hour"
                    class="tt-hour-line"
                    :style="{ top: `${(hour - startHour) * hourHeight}px` }"
                  ></span>

                  <span
                    v-if="
                      day.date === todayKey &&
                      showCurrentLine &&
                      currentLineTop !== null
                    "
                    class="tt-now-line"
                    :style="{ top: `${currentLineTop}px` }"
                  >
                    <i></i>
                  </span>

                  <button
                    v-for="course in dayCourses(day)"
                    :key="course.id"
                    class="tt-course"
                    :class="{
                      'tt-course--now': isCourseNow(course),
                      'tt-course--compact':
                        parseTimeToMinutes(course.end_time) -
                          parseTimeToMinutes(course.start_time) <=
                        60,
                    }"
                    :style="courseStyle(course)"
                    type="button"
                    :title="`${course.course_name} · ${course.teacher || '教师未录入'} · ${
                      course.location || '地点未录入'
                    }`"
                    @click="detailCourse = course"
                  >
                    <span class="tt-course__top">
                      <span class="tt-course__code">{{ course.course_code }}</span>
                      <span class="tt-course__time">
                        {{ course.start_time.slice(0, 5) }}–{{ course.end_time.slice(0, 5) }}
                      </span>
                    </span>
                    <strong>{{ course.course_name }}</strong>
                    <span v-if="course.location" class="tt-course__meta">
                      <MapPin :size="10" />
                      {{ course.location }}
                    </span>
                    <span v-if="course.teacher" class="tt-course__meta">
                      <User :size="10" />
                      {{ course.teacher }}
                    </span>
                    <span class="course-glow"></span>
                  </button>
                </div>

                <div v-if="loading" class="tt-loading">
                  <span class="spinner"></span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="emptyWeek && !loading" class="week-empty">
            <GraduationCap :size="16" />
            <span v-if="dashboard?.current_week === null">
              当前周次未启用，暂无可显示的课程。
            </span>
            <span v-else-if="dashboard?.current_week === 0">
              目标日期早于学期开始日期。
            </span>
            <span v-else>这一周没有课程安排。</span>
          </div>
        </section>

        <section class="timetable-notes">
          <article class="note-card card">
            <span class="note-icon"><CalendarDays :size="17" /></span>
            <div>
              <strong>周次过滤</strong>
              <p>
                设置学期开始日期后，看板会按每门课程的 Week 范围自动过滤；未设置时展示全部课程。
              </p>
            </div>
          </article>
          <article class="note-card card">
            <span class="note-icon"><FileUp :size="17" /></span>
            <div>
              <strong>重新导入</strong>
              <p>
                每次导入都会创建一份新课表。可以在上方切换查看，或将新导入的课表设为当前。
              </p>
            </div>
          </article>
        </section>
      </template>
    </div>

    <Modal
      v-model="importOpen"
      title="导入课表"
      subtitle="支持教务系统导出的周课表 HTML，最大 2 MB。"
      :width="590"
      :close-on-overlay="!importing"
    >
      <form class="import-form" @submit.prevent="submitImport">
        <div
          class="drop-zone"
          :class="{ 'drop-zone--active': dragging, 'drop-zone--selected': selectedFile }"
          @click="chooseFile"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            class="file-input"
            type="file"
            accept=".html,.htm,text/html"
            @change="onFileChange"
          />
          <span class="drop-zone__icon">
            <Upload v-if="!selectedFile" :size="23" />
            <GraduationCap v-else :size="23" />
          </span>
          <template v-if="selectedFile">
            <strong>{{ selectedFile.name }}</strong>
            <span>{{ (selectedFile.size / 1024).toFixed(1) }} KB · 点击重新选择</span>
          </template>
          <template v-else>
            <strong>拖入课表 HTML，或点击选择</strong>
            <span>课程代码、教师、地点和周次会自动提取</span>
          </template>
        </div>

        <div class="form-grid">
          <div class="field">
            <label for="timetable-name">课表名称</label>
            <input
              id="timetable-name"
              v-model="importForm.name"
              class="input"
              maxlength="200"
              placeholder="2026/09 Semester"
            />
          </div>
          <div class="field">
            <label for="semester-start">学期第 1 周开始日期</label>
            <input
              id="semester-start"
              v-model="importForm.semesterStartDate"
              class="input"
              type="date"
            />
            <span class="field-hint">建议选择第 1 周的周一；可稍后修改。</span>
          </div>
        </div>

        <label class="switch import-active-switch">
          <input v-model="importForm.setActive" type="checkbox" />
          <span class="switch__track"></span>
          导入后设为当前课表
        </label>

        <button class="form-submit-hidden" type="submit"></button>
      </form>

      <template #footer>
        <button class="btn" type="button" :disabled="importing" @click="importOpen = false">
          取消
        </button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="importing || !selectedFile"
          @click="submitImport"
        >
          <span v-if="importing" class="spinner spinner--small"></span>
          <Upload v-else :size="14" />
          {{ importing ? '正在解析…' : '导入课表' }}
        </button>
      </template>
    </Modal>

    <Modal
      v-model="editOpen"
      title="课表与学期设置"
      subtitle="修改展示名称，或设置用于周次计算的学期起点。"
      :width="520"
    >
      <form class="meta-form" @submit.prevent="saveMeta">
        <div class="field">
          <label for="meta-name">课表名称</label>
          <input id="meta-name" v-model="metaForm.name" class="input" maxlength="200" />
        </div>
        <div class="field">
          <label for="meta-start">第 1 周开始日期</label>
          <input id="meta-start" v-model="metaForm.semesterStartDate" class="input" type="date" />
          <span class="field-hint">留空表示只展示周课表，不按周次过滤。</span>
        </div>
        <button class="form-submit-hidden" type="submit"></button>
      </form>

      <template #footer>
        <button class="btn btn-danger footer-delete" type="button" @click="deleteSelected">
          <Trash2 :size="14" />
          删除课表
        </button>
        <button class="btn" type="button" @click="editOpen = false">取消</button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="savingMeta"
          @click="saveMeta"
        >
          <span v-if="savingMeta" class="spinner spinner--small"></span>
          保存
        </button>
      </template>
    </Modal>

    <Modal
      :model-value="Boolean(detailCourse)"
      title="课程详情"
      :subtitle="detailCourse?.course_name || ''"
      :width="460"
      @update:model-value="(open) => !open && (detailCourse = null)"
    >
      <div
        v-if="detailCourse"
        class="course-detail"
        :style="toneStyle(detailCourse.course_code)"
      >
        <div class="course-detail__hero">
          <span class="course-detail__code">{{ detailCourse.course_code }}</span>
          <h3>{{ detailCourse.course_name }}</h3>
          <span class="course-detail__week">
            {{
              detailCourse.week_start
                ? `第 ${detailCourse.week_start}–${detailCourse.week_end} 周`
                : '全部周次'
            }}
          </span>
        </div>

        <div class="course-detail__grid">
          <div class="course-detail__row">
            <span><CalendarDays :size="15" /></span>
            <div>
              <small>上课时间</small>
              <strong>
                {{ WEEKDAYS_MONDAY_FIRST[detailCourse.weekday - 1] }}
                {{ detailCourse.start_time.slice(0, 5) }}–{{
                  detailCourse.end_time.slice(0, 5)
                }}
              </strong>
            </div>
          </div>
          <div class="course-detail__row">
            <span><MapPin :size="15" /></span>
            <div>
              <small>上课地点</small>
              <strong>{{ detailCourse.location || '未录入' }}</strong>
            </div>
          </div>
          <div class="course-detail__row">
            <span><User :size="15" /></span>
            <div>
              <small>任课教师</small>
              <strong>{{ detailCourse.teacher || '未录入' }}</strong>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <button class="btn btn-primary" type="button" @click="detailCourse = null">
          关闭
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.timetable-loading {
  min-height: 50vh;
}

.empty-timetable {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(320px, 1.1fr);
  align-items: center;
  gap: 30px;
  min-height: 480px;
  padding: 48px;
  overflow: hidden;
}

.empty-timetable__visual {
  position: relative;
  display: grid;
  min-height: 300px;
  place-items: center;
}

.orb {
  position: absolute;
  border-radius: 50%;
}

.orb--one {
  width: 260px;
  height: 260px;
  border: 1px solid #d5e9dc;
  background: #eaf5ee;
}

.orb--two {
  width: 176px;
  height: 176px;
  border: 1px solid #f0ddcf;
  background: #fbf2eb;
}

.empty-icon {
  position: relative;
  display: grid;
  width: 86px;
  height: 86px;
  place-items: center;
  border: 1px solid var(--stroke-accent);
  border-radius: 28px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.empty-timetable__copy {
  max-width: 480px;
}

.empty-timetable__copy h2 {
  margin-top: 8px;
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 680;
  letter-spacing: -0.04em;
}

.empty-timetable__copy p {
  margin: 12px 0 22px;
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.75;
}

.timetable-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 16px;
}

.toolbar-select {
  display: flex;
  align-items: center;
  gap: 9px;
}

.toolbar-label {
  color: var(--text-3);
  font-size: 9.5px;
  font-weight: 620;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.timetable-select {
  width: 220px;
  height: 36px;
  font-size: 11.5px;
  background-position:
    calc(100% - 16px) 15px,
    calc(100% - 11px) 15px;
}

.toolbar-meta {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.week-nav {
  display: flex;
  flex: none;
  align-items: center;
  gap: 1px;
}

.week-nav__label {
  min-width: 174px;
  border: 0;
  color: var(--text-2);
  background: transparent;
  font-size: 10.5px;
  cursor: pointer;
}

.week-nav__label:hover {
  color: var(--text-1);
}

.timetable-card {
  margin-top: 14px;
  overflow: hidden;
  padding: 20px 0 0;
}

.timetable-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 0 22px 16px;
}

.timetable-head .section-title {
  margin-top: 5px;
}

.head-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  font-size: 10px;
}

.timetable-scroll {
  overflow-x: auto;
  border-top: 1px solid var(--stroke);
}

.timetable-frame {
  min-width: 900px;
}

.tt-header {
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(110px, 1fr));
  border-bottom: 1px solid var(--stroke);
}

.tt-gutter {
  border-right: 1px solid var(--stroke);
}

.tt-day-head {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  padding: 11px 13px;
  border-right: 1px solid var(--stroke);
  background: var(--surface-2);
}

.tt-day-name {
  color: var(--text-3);
  font-size: 8.5px;
  font-weight: 650;
  letter-spacing: 0.08em;
}

.tt-day-head strong {
  color: var(--text-2);
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 640;
  letter-spacing: -0.04em;
  line-height: 1.05;
}

.tt-day-date {
  color: var(--text-3);
  font-size: 8.5px;
}

.tt-day-head--today {
  background: var(--accent-faint);
}

.tt-day-head--today .tt-day-name,
.tt-day-head--today strong {
  color: var(--accent-deep);
}

.tt-body {
  position: relative;
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(110px, 1fr));
  height: var(--tt-height);
  min-height: 400px;
}

.tt-times {
  position: relative;
  height: var(--tt-height);
}

.tt-time {
  position: absolute;
  right: 8px;
  transform: translateY(-5px);
  color: var(--text-3);
  font-size: 8px;
  font-variant-numeric: tabular-nums;
}

.tt-day-column {
  position: relative;
  height: var(--tt-height);
  border-right: 1px solid var(--stroke);
}

.tt-day-column--today {
  background: var(--accent-faint);
}

.tt-hour-line {
  position: absolute;
  right: 0;
  left: 0;
  border-top: 1px solid var(--stroke);
}

.tt-now-line {
  position: absolute;
  right: 0;
  left: 0;
  z-index: 4;
  height: 1px;
  background: var(--accent);
}

.tt-now-line i {
  position: absolute;
  top: -3px;
  left: -3px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}

.tt-course {
  position: absolute;
  right: 5px;
  left: 5px;
  z-index: 2;
  display: flex;
  min-height: 28px;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  overflow: hidden;
  border: 1px solid var(--tone-border);
  border-left: 2px solid var(--tone);
  border-radius: 8px;
  color: var(--text-1);
  background: var(--tone-bg);
  text-align: left;
  cursor: pointer;
  transition: background 160ms var(--ease-out);
}

.tt-course:hover {
  z-index: 5;
  background: var(--tone-bg-strong);
}

.tt-course--now {
  box-shadow: 0 0 0 2px var(--tone);
}

.tt-course__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  overflow: hidden;
}

.tt-course__code {
  color: var(--tone);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.tt-course__time {
  overflow: hidden;
  color: var(--text-3);
  font-size: 7.5px;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tt-course > strong {
  display: -webkit-box;
  overflow: hidden;
  font-size: 10.5px;
  font-weight: 620;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.tt-course__meta {
  display: flex;
  align-items: center;
  gap: 3px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tt-course--compact {
  gap: 1px;
  padding-block: 4px;
}

.tt-course--compact .tt-course__time,
.tt-course--compact .tt-course__meta {
  display: none;
}

.tt-course--compact > strong {
  -webkit-line-clamp: 1;
}

.course-glow {
  display: none;
}

.tt-loading {
  position: absolute;
  inset: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
}

.week-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid var(--stroke);
  color: var(--text-3);
  font-size: 10.5px;
}

.timetable-notes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}

.note-card {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 15px 17px;
}

.note-icon {
  display: grid;
  width: 32px;
  height: 32px;
  flex: none;
  place-items: center;
  border-radius: 10px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.note-card strong {
  font-size: 11.5px;
  font-weight: 600;
}

.note-card p {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 10px;
  line-height: 1.55;
}

.warning-banner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  padding: 13px 15px;
  border: 1px solid color-mix(in srgb, var(--warning) 20%, white);
  border-radius: 13px;
  color: var(--warning);
  background: var(--warning-soft);
}

.warning-banner strong {
  font-size: 11.5px;
}

.warning-banner p {
  margin-top: 3px;
  color: color-mix(in srgb, var(--warning) 76%, var(--text-2));
  font-size: 10px;
}

.import-form,
.meta-form {
  display: flex;
  flex-direction: column;
  gap: 17px;
}

.drop-zone {
  display: flex;
  min-height: 156px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px dashed var(--stroke-strong);
  border-radius: 15px;
  color: var(--text-2);
  background: var(--accent-faint);
  text-align: center;
  cursor: pointer;
  transition:
    border-color 160ms var(--ease-out),
    background 160ms var(--ease-out);
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--accent-deep);
  background: var(--accent-soft);
}

.drop-zone--selected {
  border-style: solid;
  border-color: var(--stroke-accent);
}

.drop-zone__icon {
  display: grid;
  width: 44px;
  height: 44px;
  margin-bottom: 3px;
  place-items: center;
  border-radius: 13px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.drop-zone strong {
  font-size: 12.5px;
  font-weight: 590;
}

.drop-zone span:not(.drop-zone__icon) {
  color: var(--text-3);
  font-size: 10px;
}

.file-input {
  display: none;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.import-active-switch {
  align-self: flex-start;
}

.footer-delete {
  margin-right: auto;
}

.form-submit-hidden {
  display: none;
}

.spinner--small {
  width: 13px;
  height: 13px;
  border-width: 1.5px;
}

.course-detail__hero {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border: 1px solid var(--tone-border);
  border-radius: 14px;
  background: var(--tone-bg);
}

.course-detail__code {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 5px;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 12%, transparent);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.course-detail__hero h3 {
  margin-top: 8px;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.25;
}

.course-detail__week {
  display: inline-block;
  margin-top: 8px;
  color: var(--text-3);
  font-size: 10px;
}

.course-detail__grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 15px;
}

.course-detail__row {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--stroke);
}

.course-detail__row:last-child {
  border-bottom: 0;
}

.course-detail__row > span {
  display: grid;
  width: 30px;
  height: 30px;
  flex: none;
  place-items: center;
  border-radius: 9px;
  color: var(--text-2);
  background: var(--surface-2);
}

.course-detail__row > div {
  display: flex;
  flex-direction: column;
}

.course-detail__row small {
  color: var(--text-3);
  font-size: 8.5px;
}

.course-detail__row strong {
  margin-top: 1px;
  color: var(--text-1);
  font-size: 11.5px;
  font-weight: 560;
}

@media (max-width: 1080px) {
  .timetable-toolbar {
    flex-wrap: wrap;
  }

  .toolbar-meta {
    order: 3;
    flex-basis: 100%;
  }

  .week-nav {
    margin-left: auto;
  }
}

@media (max-width: 820px) {
  .empty-timetable {
    grid-template-columns: 1fr;
    padding: 28px;
  }

  .empty-timetable__visual {
    min-height: 190px;
  }

  .orb--one {
    width: 180px;
    height: 180px;
  }

  .orb--two {
    width: 126px;
    height: 126px;
  }

  .timetable-notes {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
