<script setup>
import {
  BookOpen,
  CalendarDays,
  Plus,
  Save,
  Search,
  Trash2,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { diaryApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDialogStore } from '@/stores/dialog'
import { useToastStore } from '@/stores/toast'
import { MOODS, WEATHER_OPTIONS, moodMeta, toneStyle } from '@/utils/colors'
import {
  WEEKDAYS_CN,
  dateKey,
  formatDate,
  parseDateKey,
  relativeTimeLabel,
} from '@/utils/date'

const toast = useToastStore()
const dialog = useDialogStore()

const entries = ref([])
const total = ref(0)
const loading = ref(true)
const saving = ref(false)
const search = ref('')
const selected = ref(null)
const mode = ref('none')
const snapshot = ref('')
const editor = ref(null)

const draft = reactive({
  entry_date: dateKey(),
  title: '',
  content: '',
  mood: '',
  weather: '',
})

let searchTimer = null

const dirty = computed(() => {
  if (mode.value === 'none') return false
  return JSON.stringify(draftPayload()) !== snapshot.value
})

const wordCount = computed(() => {
  const text = draft.content.trim()
  if (!text) return 0
  return text.replace(/\s/g, '').length
})

const filteredHint = computed(() => {
  if (loading.value) return '正在读取…'
  return `${total.value} 篇`
})

const selectedMood = computed(() => moodMeta(draft.mood))

function draftPayload() {
  return {
    entry_date: draft.entry_date,
    title: draft.title,
    content: draft.content,
    mood: draft.mood,
    weather: draft.weather,
  }
}

function takeSnapshot() {
  snapshot.value = JSON.stringify(draftPayload())
}

function fillDraft(entry) {
  draft.entry_date = entry.entry_date
  draft.title = entry.title || ''
  draft.content = entry.content
  draft.mood = entry.mood || ''
  draft.weather = entry.weather || ''
  takeSnapshot()
}

function entryDateParts(entry) {
  const date = parseDateKey(entry.entry_date)
  return {
    day: String(date?.getDate() ?? '').padStart(2, '0'),
    month: date ? `${date.getMonth() + 1}月` : '',
    weekday: date ? WEEKDAYS_CN[date.getDay()] : '',
  }
}

function moodFor(entry) {
  return moodMeta(entry.mood)
}

function excerpt(entry) {
  return entry.content.replace(/\s+/g, ' ').slice(0, 56)
}

async function loadEntries({ selectId = null } = {}) {
  loading.value = true
  try {
    const result = await diaryApi.list({
      search: search.value.trim() || undefined,
      sort_by: 'entry_date',
      sort_order: 'desc',
      limit: 200,
    })
    entries.value = result.items
    total.value = result.total

    if (selectId) {
      const found = entries.value.find((item) => item.id === selectId)
      if (found) activateEntry(found)
      return
    }

    if (!result.items.length) {
      if (!selected.value) {
        mode.value = 'none'
      }
      return
    }

    const found = selected.value
      ? result.items.find((item) => item.id === selected.value.id)
      : null
    if (found && mode.value === 'edit') {
      selected.value = found
    } else if (mode.value === 'none') {
      activateEntry(result.items[0])
    }
  } catch (error) {
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

async function confirmDiscard() {
  if (!dirty.value) return true
  return dialog.ask({
    title: '放弃未保存的内容？',
    message: '当前日记有未保存的修改，切换后将丢失。',
    confirmText: '放弃修改',
    danger: true,
  })
}

function activateEntry(entry) {
  selected.value = entry
  mode.value = 'edit'
  fillDraft(entry)
}

async function requestSelect(entry) {
  if (selected.value?.id === entry.id && mode.value === 'edit') return
  if (!(await confirmDiscard())) return
  activateEntry(entry)
}

async function startCreate() {
  if (!(await confirmDiscard())) return

  const today = dateKey()
  try {
    const todayEntry = await diaryApi.byDate(today)
    activateEntry(todayEntry)
    toast.info('今天已经有一篇日记，已为你打开')
    return
  } catch (error) {
    if (error.status !== 404) {
      toast.error(error.message)
      return
    }
  }

  selected.value = null
  mode.value = 'create'
  draft.entry_date = today
  draft.title = ''
  draft.content = ''
  draft.mood = ''
  draft.weather = ''
  takeSnapshot()
  requestAnimationFrame(() => editor.value?.focus())
}

async function saveEntry() {
  if (!draft.content.trim()) {
    toast.warning('日记正文不能为空')
    return
  }
  saving.value = true
  const payload = {
    entry_date: draft.entry_date,
    title: draft.title.trim() || null,
    content: draft.content,
    mood: draft.mood || null,
    weather: draft.weather || null,
  }

  try {
    let saved
    if (selected.value?.id) {
      saved = await diaryApi.update(selected.value.id, payload)
      toast.success('日记已更新')
    } else {
      saved = await diaryApi.create(payload)
      toast.success('日记已保存')
    }
    search.value = ''
    await loadEntries({ selectId: saved.id })
  } catch (error) {
    toast.error(error.message)
  } finally {
    saving.value = false
  }
}

async function deleteEntry() {
  if (!selected.value) return
  const confirmed = await dialog.ask({
    title: '删除日记',
    message: `确定删除 ${formatDate(selected.value.entry_date)} 的日记吗？此操作无法撤销。`,
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  try {
    await diaryApi.remove(selected.value.id)
    toast.success('日记已删除')
    selected.value = null
    mode.value = 'none'
    snapshot.value = ''
    await loadEntries()
    if (!entries.value.length) mode.value = 'none'
  } catch (error) {
    toast.error(error.message)
  }
}

function scheduleSearch() {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => loadEntries(), 260)
}

function onEditorKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    if (mode.value !== 'none') saveEntry()
  }
}

onMounted(() => {
  loadEntries()
  window.addEventListener('keydown', onEditorKeydown)
})

onBeforeUnmount(() => {
  if (searchTimer) window.clearTimeout(searchTimer)
  window.removeEventListener('keydown', onEditorKeydown)
})
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <PageHeader
        eyebrow="JOURNAL"
        title="日记"
        description="给每天留下一点纹理。哪怕只写下一句话，也是在认真生活。"
      >
        <template #actions>
          <span class="chip">{{ filteredHint }}</span>
          <button class="btn btn-primary" type="button" @click="startCreate">
            <Plus :size="15" />
            写今天
          </button>
        </template>
      </PageHeader>

      <section class="diary-layout">
        <aside class="diary-list card">
          <header class="diary-list__head">
            <div class="search-box">
              <Search :size="14" class="search-icon" />
              <input
                v-model="search"
                class="input"
                placeholder="搜索日记…"
                @input="scheduleSearch"
              />
            </div>
          </header>

          <div v-if="loading" class="loading-state">
            <span class="spinner"></span>
          </div>

          <EmptyState
            v-else-if="!entries.length"
            :title="search ? '没有找到日记' : '还没有日记'"
            :description="search ? '试试更短的关键词。' : '从今天开始，留下第一段记录。'"
            :icon="BookOpen"
          >
            <button v-if="!search" class="btn btn-sm" type="button" @click="startCreate">
              <Plus :size="14" /> 写第一篇
            </button>
          </EmptyState>

          <div v-else class="entry-list">
            <button
              v-for="entry in entries"
              :key="entry.id"
              class="entry-item"
              :class="{ 'entry-item--active': selected?.id === entry.id && mode === 'edit' }"
              type="button"
              @click="requestSelect(entry)"
            >
              <span class="entry-date">
                <strong>{{ entryDateParts(entry).day }}</strong>
                <span>{{ entryDateParts(entry).month }}</span>
              </span>
              <span class="entry-copy">
                <span class="entry-topline">
                  <strong>{{ entry.title || '无题日记' }}</strong>
                  <span v-if="moodFor(entry)" class="entry-mood">{{ moodFor(entry).emoji }}</span>
                </span>
                <span class="entry-excerpt">{{ excerpt(entry) }}</span>
                <span class="entry-meta">
                  {{ entryDateParts(entry).weekday }}
                  <i></i>
                  {{ relativeTimeLabel(entry.updated_at) }}
                </span>
              </span>
              <span class="entry-indicator"></span>
            </button>
          </div>
        </aside>

        <article v-if="mode !== 'none'" class="diary-editor card" :style="toneStyle(selectedMood?.label || draft.mood || 'diary')">
          <header class="editor-head">
            <div class="editor-date">
              <CalendarDays :size="15" />
              <input v-model="draft.entry_date" type="date" class="editor-date-input" />
              <span v-if="dirty" class="unsaved-dot"></span>
              <span v-if="dirty" class="unsaved-label">未保存</span>
            </div>
            <div class="editor-actions">
              <button
                v-if="selected"
                class="icon-btn icon-btn--danger"
                type="button"
                title="删除日记"
                @click="deleteEntry"
              >
                <Trash2 :size="16" />
              </button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="saving" @click="saveEntry">
                <span v-if="saving" class="spinner spinner--small"></span>
                <Save v-else :size="14" />
                {{ saving ? '保存中' : '保存' }}
              </button>
            </div>
          </header>

          <div class="editor-scroll">
            <div class="editor-title-row">
              <span v-if="selectedMood" class="editor-mood">{{ selectedMood.emoji }}</span>
              <input
                v-model="draft.title"
                class="editor-title"
                maxlength="200"
                placeholder="给这一天一个标题…"
              />
            </div>

            <div class="mood-row">
              <span class="editor-label">心情</span>
              <button
                v-for="mood in MOODS"
                :key="mood.value"
                class="mood-chip"
                :class="{ active: draft.mood === mood.value }"
                type="button"
                @click="draft.mood = draft.mood === mood.value ? '' : mood.value"
              >
                <span>{{ mood.emoji }}</span>
                {{ mood.label }}
              </button>
            </div>

            <div class="mood-row">
              <span class="editor-label">天气</span>
              <button
                v-for="weather in WEATHER_OPTIONS"
                :key="weather"
                class="weather-chip"
                :class="{ active: draft.weather === weather }"
                type="button"
                @click="draft.weather = draft.weather === weather ? '' : weather"
              >
                {{ weather }}
              </button>
            </div>

            <div class="editor-divider"></div>

            <textarea
              ref="editor"
              v-model="draft.content"
              class="editor-content"
              maxlength="100000"
              placeholder="今天发生了什么？此刻的你，在想些什么？"
            ></textarea>
          </div>

          <footer class="editor-footer">
            <span class="editor-stats">{{ wordCount }} 字</span>
            <span class="editor-hint">⌘ / Ctrl + S 保存</span>
            <span v-if="selected" class="editor-hint">
              创建于 {{ formatDate(selected.created_at) }}
            </span>
          </footer>
        </article>

        <article v-else class="diary-empty card">
          <div class="diary-empty__rings"></div>
          <span class="diary-empty__icon"><BookOpen :size="28" :stroke-width="1.4" /></span>
          <h2>写下今天的第一句话</h2>
          <p>日记会保存在本地 SQLite 数据库中，只有你能看到。</p>
          <button class="btn btn-primary" type="button" @click="startCreate">
            <Plus :size="15" />
            开始写日记
          </button>
        </article>
      </section>
    </div>
  </div>
</template>

<style scoped>
.diary-layout {
  display: grid;
  grid-template-columns: minmax(280px, 330px) minmax(0, 1fr);
  gap: 14px;
  min-height: 600px;
  align-items: stretch;
}

.diary-list {
  display: flex;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  padding: 12px;
}

.diary-list__head {
  padding-bottom: 10px;
}

.diary-list__head .input {
  height: 37px;
}

.entry-list {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  padding-right: 2px;
}

.entry-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 11px;
  width: 100%;
  padding: 11px 10px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: var(--text-2);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition:
    background 150ms var(--ease-out),
    border-color 150ms var(--ease-out);
}

.entry-item:hover {
  background: var(--surface-2);
}

.entry-item--active {
  border-color: var(--stroke-accent);
  background: var(--accent-soft);
}

.entry-date {
  display: flex;
  width: 41px;
  min-height: 46px;
  flex: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  border: 1px solid var(--stroke);
  border-radius: 10px;
  background: var(--surface-2);
}

.entry-date strong {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 650;
  letter-spacing: -0.04em;
  line-height: 1;
}

.entry-date span {
  margin-top: 3px;
  color: var(--text-3);
  font-size: 8px;
}

.entry-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.entry-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.entry-topline strong {
  overflow: hidden;
  color: var(--text-1);
  font-size: 11.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-mood {
  font-size: 12px;
}

.entry-excerpt {
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 9.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  color: var(--text-3);
  font-size: 8.5px;
}

.entry-meta i {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: currentColor;
}

.entry-indicator {
  position: absolute;
  top: 50%;
  right: 2px;
  width: 3px;
  height: 16px;
  border-radius: 3px 0 0 3px;
  background: transparent;
  transform: translateY(-50%);
}

.entry-item--active .entry-indicator {
  background: var(--accent);
}

.diary-editor {
  display: flex;
  min-height: 600px;
  flex-direction: column;
  overflow: hidden;
  border-color: color-mix(in srgb, var(--tone, var(--accent)) 11%, var(--stroke));
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 20px;
  border-bottom: 1px solid var(--stroke);
  background: var(--surface-2);
}

.editor-date {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-3);
}

.editor-date-input {
  width: 130px;
  padding: 2px 0;
  border: 0;
  outline: none;
  color: var(--text-2);
  background: transparent;
  font-size: 10.5px;
  color-scheme: dark;
}

.editor-date-input::-webkit-calendar-picker-indicator {
  opacity: 0.42;
}

.unsaved-dot {
  width: 5px;
  height: 5px;
  margin-left: 2px;
  border-radius: 50%;
  background: var(--warning);
}

.unsaved-label {
  color: var(--warning);
  font-size: 9px;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.editor-scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  padding: 30px clamp(24px, 4vw, 58px) 20px;
}

.editor-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-mood {
  flex: none;
  font-size: 23px;
}

.editor-title {
  width: 100%;
  padding: 0;
  border: 0;
  outline: none;
  color: var(--text-1);
  background: transparent;
  font-family: var(--font-display);
  font-size: clamp(24px, 2.8vw, 34px);
  font-weight: 660;
  letter-spacing: -0.04em;
  line-height: 1.3;
}

.editor-title::placeholder {
  color: var(--text-3);
  opacity: 0.55;
}

.mood-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  margin-top: 16px;
}

.editor-label {
  min-width: 34px;
  margin-right: 3px;
  color: var(--text-3);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.mood-chip,
.weather-chip {
  display: inline-flex;
  height: 27px;
  align-items: center;
  gap: 4px;
  padding: 0 9px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-3);
  background: transparent;
  font-size: 9.5px;
  cursor: pointer;
  transition: 150ms var(--ease-out);
}

.mood-chip:hover,
.weather-chip:hover {
  border-color: var(--stroke-strong);
  color: var(--text-1);
  background: var(--surface-2);
}

.mood-chip.active {
  border-color: var(--stroke-accent);
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.weather-chip.active {
  border-color: color-mix(in srgb, var(--warning) 22%, white);
  color: var(--warning);
  background: var(--warning-soft);
}

.editor-divider {
  height: 1px;
  margin: 23px 0 19px;
  background: var(--stroke);
}

.editor-content {
  width: 100%;
  min-height: 340px;
  flex: 1;
  padding: 0;
  border: 0;
  outline: none;
  color: var(--text-1);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.9;
  resize: none;
}

.editor-content::placeholder {
  color: var(--text-3);
  opacity: 0.55;
}

.editor-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 11px 20px;
  border-top: 1px solid var(--stroke);
  color: var(--text-3);
  font-size: 9px;
}

.editor-stats {
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}

.editor-hint:last-child {
  margin-left: auto;
}

.diary-empty {
  display: flex;
  min-height: 600px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  overflow: hidden;
  padding: 40px;
  text-align: center;
}

.diary-empty__rings {
  position: absolute;
  width: 440px;
  height: 440px;
  border: 1px solid #e3eee6;
  border-radius: 50%;
  background: #f7fbf8;
  pointer-events: none;
}

.diary-empty__icon {
  position: relative;
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  border: 1px solid var(--stroke-accent);
  border-radius: 22px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.diary-empty h2 {
  position: relative;
  margin-top: 4px;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -0.035em;
}

.diary-empty p {
  position: relative;
  max-width: 340px;
  color: var(--text-3);
  font-size: 11.5px;
}

.diary-empty .btn {
  position: relative;
  margin-top: 8px;
}

.spinner--small {
  width: 13px;
  height: 13px;
  border-width: 1.5px;
}

@media (max-width: 1020px) {
  .diary-layout {
    grid-template-columns: 270px minmax(0, 1fr);
  }
}

@media (max-width: 820px) {
  .diary-layout {
    grid-template-columns: 1fr;
  }

  .diary-list {
    max-height: 300px;
  }

  .diary-editor,
  .diary-empty {
    min-height: 520px;
  }
}
</style>
