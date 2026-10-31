<script setup>
import {
  CalendarClock,
  Check,
  CheckCircle2,
  Circle,
  ListTodo,
  Pencil,
  Plus,
  Search,
  Trash2,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import { todosApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDialogStore } from '@/stores/dialog'
import { useToastStore } from '@/stores/toast'
import { formatDueDate, formatRelativeDay, isoToLocalInput, localInputToIso } from '@/utils/date'

const toast = useToastStore()
const dialog = useDialogStore()

const tasks = ref([])
const total = ref(0)
const loading = ref(true)
const saving = ref(false)
const togglingId = ref(null)
const filter = ref('open')
const priority = ref('')
const search = ref('')
const formOpen = ref(false)
const editing = ref(null)

const form = reactive({
  title: '',
  description: '',
  status: 'pending',
  priority: 'medium',
  dueLocal: '',
})

const priorityMeta = {
  high: { label: '高优先级', className: 'priority--high' },
  medium: { label: '中优先级', className: 'priority--medium' },
  low: { label: '低优先级', className: 'priority--low' },
}

const statusMeta = {
  pending: { label: '待处理', className: 'status--pending' },
  in_progress: { label: '进行中', className: 'status--progress' },
  completed: { label: '已完成', className: 'status--done' },
}

const filters = [
  { value: 'open', label: '未完成' },
  { value: 'all', label: '全部' },
  { value: 'completed', label: '已完成' },
]

const countLabel = computed(() => (loading.value ? '同步中' : `${total.value} 项`))
const activeFilterLabel = computed(
  () => filters.find((item) => item.value === filter.value)?.label || '',
)

let searchTimer = null

async function loadTasks() {
  loading.value = true
  try {
    const params = {
      search: search.value.trim() || undefined,
      priority: priority.value || undefined,
      sort_by: 'due_at',
      sort_order: 'asc',
      limit: 200,
    }
    if (filter.value === 'open') {
      params.status = ['pending', 'in_progress']
    } else if (filter.value === 'completed') {
      params.status = ['completed']
    }
    const result = await todosApi.list(params)
    tasks.value = result.items
    total.value = result.total
  } catch (error) {
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

function scheduleLoad() {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadTasks, 240)
}

watch([filter, priority], loadTasks)
watch(search, scheduleLoad)

function resetForm() {
  form.title = ''
  form.description = ''
  form.status = 'pending'
  form.priority = 'medium'
  form.dueLocal = ''
}

function openCreate() {
  editing.value = null
  resetForm()
  formOpen.value = true
}

function openEdit(task) {
  editing.value = task
  form.title = task.title
  form.description = task.description || ''
  form.status = task.status
  form.priority = task.priority
  form.dueLocal = isoToLocalInput(task.due_at)
  formOpen.value = true
}

async function saveTask() {
  if (!form.title.trim()) {
    toast.warning('请填写待办标题')
    return
  }
  saving.value = true
  const payload = {
    title: form.title.trim(),
    description: form.description.trim() || null,
    status: form.status,
    priority: form.priority,
    due_at: form.dueLocal ? localInputToIso(form.dueLocal) : null,
  }

  try {
    if (editing.value) {
      await todosApi.update(editing.value.id, payload)
      toast.success('待办已更新')
    } else {
      await todosApi.create(payload)
      toast.success('待办已创建')
    }
    formOpen.value = false
    await loadTasks()
  } catch (error) {
    toast.error(error.message)
  } finally {
    saving.value = false
  }
}

async function toggleTask(task) {
  if (togglingId.value) return
  togglingId.value = task.id
  try {
    await todosApi.update(task.id, {
      status: task.status === 'completed' ? 'pending' : 'completed',
    })
    await loadTasks()
  } catch (error) {
    toast.error(error.message)
  } finally {
    togglingId.value = null
  }
}

async function deleteTask(task) {
  const confirmed = await dialog.ask({
    title: '删除待办',
    message: `确定删除「${task.title}」吗？此操作无法撤销。`,
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  try {
    await todosApi.remove(task.id)
    toast.success('待办已删除')
    await loadTasks()
  } catch (error) {
    toast.error(error.message)
  }
}

function isOverdue(task) {
  return task.is_overdue
}

onMounted(loadTasks)
onBeforeUnmount(() => {
  if (searchTimer) window.clearTimeout(searchTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <PageHeader
        eyebrow="TASKS"
        title="待办清单"
        description="把脑中的承诺放到一个可靠的地方，然后专注完成眼前这一件。"
      >
        <template #actions>
          <span class="chip">{{ countLabel }}</span>
          <button class="btn btn-primary" type="button" @click="openCreate">
            <Plus :size="15" />
            新建待办
          </button>
        </template>
      </PageHeader>

      <section class="toolbar card">
        <div class="toolbar-left">
          <div class="segmented">
            <button
              v-for="item in filters"
              :key="item.value"
              type="button"
              :class="{ active: filter === item.value }"
              @click="filter = item.value"
            >
              {{ item.label }}
            </button>
          </div>
          <select v-model="priority" class="select priority-select" aria-label="优先级筛选">
            <option value="">全部优先级</option>
            <option value="high">高优先级</option>
            <option value="medium">中优先级</option>
            <option value="low">低优先级</option>
          </select>
        </div>
        <div class="search-box toolbar-search">
          <Search :size="15" class="search-icon" />
          <input v-model="search" class="input" placeholder="搜索标题或描述…" />
        </div>
      </section>

      <section class="task-section">
        <div class="list-caption">
          <span>{{ activeFilterLabel }} · {{ tasks.length }} 条</span>
          <span v-if="priority" class="subtle">已按优先级筛选</span>
        </div>

        <div v-if="loading" class="task-list">
          <div v-for="index in 4" :key="index" class="task-skeleton card">
            <span class="skeleton skeleton-check"></span>
            <div class="task-skeleton__copy">
              <span class="skeleton" style="width: 38%; height: 13px"></span>
              <span class="skeleton" style="width: 68%; height: 10px"></span>
            </div>
          </div>
        </div>

        <EmptyState
          v-else-if="!tasks.length"
          :title="search ? '没有匹配的待办' : '清单已经很干净'"
          :description="
            search
              ? '试试更换关键词，或者清空筛选条件。'
              : '新建一件待办，让今天有一个清晰的起点。'
          "
          :icon="ListTodo"
        >
          <button v-if="!search" class="btn btn-sm" type="button" @click="openCreate">
            <Plus :size="14" />
            新建待办
          </button>
        </EmptyState>

        <div v-else class="task-list">
          <article
            v-for="task in tasks"
            :key="task.id"
            class="task-item card"
            :class="{ 'task-item--done': task.status === 'completed' }"
          >
            <button
              class="task-check"
              :class="{ 'task-check--done': task.status === 'completed' }"
              :disabled="togglingId === task.id"
              type="button"
              :title="task.status === 'completed' ? '标记为未完成' : '标记为已完成'"
              @click="toggleTask(task)"
            >
              <Check v-if="task.status === 'completed'" :size="13" :stroke-width="2.4" />
              <Circle v-else :size="11" />
            </button>

            <div class="task-body">
              <div class="task-heading">
                <h3>{{ task.title }}</h3>
                <span class="priority-pill" :class="priorityMeta[task.priority].className">
                  {{ priorityMeta[task.priority].label }}
                </span>
                <span
                  class="status-pill"
                  :class="statusMeta[task.status].className"
                >
                  {{ statusMeta[task.status].label }}
                </span>
                <span v-if="isOverdue(task)" class="chip chip--danger overdue-chip">已逾期</span>
              </div>

              <p v-if="task.description" class="task-description">{{ task.description }}</p>

              <div class="task-meta">
                <span v-if="task.due_at" class="task-meta__item" :class="{ 'task-meta__item--late': isOverdue(task) }">
                  <CalendarClock :size="13" />
                  {{ formatDueDate(task.due_at) }}
                </span>
                <span v-else class="task-meta__item">
                  <CalendarClock :size="13" />
                  未设置截止时间
                </span>
                <span class="task-meta__item">
                  <CheckCircle2 :size="13" />
                  {{ task.completed_at ? `完成于 ${formatRelativeDay(task.completed_at)}` : '尚未完成' }}
                </span>
              </div>
            </div>

            <div class="task-actions">
              <button class="icon-btn" type="button" title="编辑" @click="openEdit(task)">
                <Pencil :size="15" />
              </button>
              <button
                class="icon-btn icon-btn--danger"
                type="button"
                title="删除"
                @click="deleteTask(task)"
              >
                <Trash2 :size="15" />
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <Modal
      v-model="formOpen"
      :title="editing ? '编辑待办' : '新建待办'"
      subtitle="清晰具体的描述，会让行动更容易发生。"
      :width="520"
    >
      <form class="task-form" @submit.prevent="saveTask">
        <div class="field">
          <label for="task-title">标题</label>
          <input
            id="task-title"
            v-model="form.title"
            class="input"
            maxlength="200"
            placeholder="例如：完成数据库课程设计"
            autofocus
          />
        </div>

        <div class="field">
          <label for="task-description">描述</label>
          <textarea
            id="task-description"
            v-model="form.description"
            class="textarea task-description-input"
            maxlength="5000"
            placeholder="补充背景、下一步行动或验收标准…"
          ></textarea>
        </div>

        <div class="form-grid">
          <div class="field">
            <label for="task-status">状态</label>
            <select id="task-status" v-model="form.status" class="select">
              <option value="pending">待处理</option>
              <option value="in_progress">进行中</option>
              <option value="completed">已完成</option>
            </select>
          </div>
          <div class="field">
            <label for="task-priority">优先级</label>
            <select id="task-priority" v-model="form.priority" class="select">
              <option value="high">高优先级</option>
              <option value="medium">中优先级</option>
              <option value="low">低优先级</option>
            </select>
          </div>
        </div>

        <div class="field">
          <label for="task-due">截止时间</label>
          <input
            id="task-due"
            v-model="form.dueLocal"
            class="input"
            type="datetime-local"
          />
          <span class="field-hint">留空表示没有明确的截止时间。</span>
        </div>

        <button class="form-submit-hidden" type="submit"></button>
      </form>

      <template #footer>
        <button class="btn" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="saving" @click="saveTask">
          <span v-if="saving" class="spinner spinner--small"></span>
          {{ editing ? '保存修改' : '创建待办' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 14px;
  border-radius: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 9px;
}

.priority-select {
  width: 136px;
  height: 36px;
  font-size: 12px;
  background-position:
    calc(100% - 16px) 15px,
    calc(100% - 11px) 15px;
}

.toolbar-search {
  width: min(340px, 38vw);
}

.toolbar-search .input {
  height: 36px;
}

.task-section {
  margin-top: 18px;
}

.list-caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 10px;
  color: var(--text-3);
  font-size: 10.5px;
  letter-spacing: 0.02em;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 14px 16px 18px;
  border-radius: 16px;
  transition:
    border-color 160ms var(--ease-out),
    background 160ms var(--ease-out),
    transform 160ms var(--ease-out);
}

.task-item:hover {
  border-color: var(--stroke-strong);
  background:
    linear-gradient(155deg, rgba(255, 255, 255, 0.045), transparent 50%),
    var(--surface-1);
  transform: translateY(-1px);
}

.task-item--done {
  opacity: 0.64;
}

.task-check {
  display: grid;
  width: 23px;
  height: 23px;
  flex: none;
  margin-top: 2px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  color: transparent;
  background: transparent;
  cursor: pointer;
  transition: 160ms var(--ease-out);
}

.task-check:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.task-check--done {
  border-color: var(--accent);
  color: #03111b;
  background: var(--accent);
}

.task-body {
  min-width: 0;
  flex: 1;
}

.task-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.task-heading h3 {
  margin-right: 2px;
  overflow-wrap: anywhere;
  font-size: 14px;
  font-weight: 610;
  letter-spacing: -0.01em;
}

.task-item--done .task-heading h3 {
  color: var(--text-2);
  text-decoration: line-through;
  text-decoration-color: var(--text-3);
}

.priority-pill,
.status-pill {
  padding: 2px 7px;
  border-radius: 5px;
  font-size: 9px;
  font-weight: 650;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.priority--high {
  color: var(--danger);
  background: var(--danger-soft);
}

.priority--medium {
  color: var(--warning);
  background: var(--warning-soft);
}

.priority--low {
  color: var(--success);
  background: var(--success-soft);
}

.status--pending {
  color: var(--text-3);
  background: rgba(255, 255, 255, 0.05);
}

.status--progress {
  color: var(--accent);
  background: var(--accent-soft);
}

.status--done {
  color: var(--success);
  background: var(--success-soft);
}

.overdue-chip {
  padding: 1px 6px;
  font-size: 8.5px;
}

.task-description {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 11.5px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 9px;
}

.task-meta__item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-3);
  font-size: 9.5px;
}

.task-meta__item--late {
  color: var(--danger);
}

.task-actions {
  display: flex;
  flex: none;
  gap: 1px;
  opacity: 0;
  transition: opacity 160ms var(--ease-out);
}

.task-item:hover .task-actions,
.task-item:focus-within .task-actions {
  opacity: 1;
}

.task-skeleton {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
}

.skeleton-check {
  width: 23px;
  height: 23px;
  flex: none;
  border-radius: 8px;
}

.task-skeleton__copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
}

.task-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-description-input {
  min-height: 104px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-submit-hidden {
  display: none;
}

.spinner--small {
  width: 13px;
  height: 13px;
  border-width: 1.5px;
}

@media (max-width: 760px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-left {
    flex-wrap: wrap;
  }

  .toolbar-search {
    width: 100%;
  }

  .task-actions {
    opacity: 1;
  }
}
</style>
