<script setup>
import {
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Pencil,
  Plus,
  Trash2,
  TrendingDown,
  TrendingUp,
  Wallet,
} from '@lucide/vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { ledgerApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import MetricCard from '@/components/MetricCard.vue'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDialogStore } from '@/stores/dialog'
import { useToastStore } from '@/stores/toast'
import { toneFor, toneStyle } from '@/utils/colors'
import {
  addMonths,
  dateKey,
  formatDateLong,
  formatMonthTitle,
  formatTime,
  isoToLocalInput,
  localInputToIso,
  monthRangeIso,
  startOfMonth,
} from '@/utils/date'
import {
  centsToYuanInput,
  formatMoney,
  yuanToCents,
} from '@/utils/money'

const toast = useToastStore()
const dialog = useDialogStore()

const currentMonth = ref(startOfMonth(new Date()))
const typeFilter = ref('all')
const transactions = ref([])
const summary = ref(null)
const loading = ref(true)
const saving = ref(false)
const formOpen = ref(false)
const editing = ref(null)

const form = reactive({
  type: 'expense',
  amountYuan: '',
  category: '',
  note: '',
  occurredLocal: isoToLocalInput(new Date().toISOString()),
})

const categorySuggestions = [
  '餐饮',
  '交通',
  '购物',
  '学习',
  '居住',
  '娱乐',
  '医疗',
  '通讯',
  '工资',
  '奖金',
  '理财',
  '其他',
]

const monthLabel = computed(() => formatMonthTitle(currentMonth.value))
const range = computed(() => monthRangeIso(currentMonth.value))

const groupedTransactions = computed(() => {
  const groups = new Map()
  for (const item of transactions.value) {
    const key = dateKey(item.occurred_at)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(item)
  }
  return [...groups.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, items]) => ({
      key,
      label: formatDateLong(new Date(itemDate(items[0]))),
      income: items
        .filter((item) => item.type === 'income')
        .reduce((sum, item) => sum + item.amount_cents, 0),
      expense: items
        .filter((item) => item.type === 'expense')
        .reduce((sum, item) => sum + item.amount_cents, 0),
      items,
    }))
})

const expenseGroups = computed(() => {
  const groups = summary.value?.groups || []
  const total = summary.value?.expense_cents || 0
  return groups
    .filter((group) => group.expense_cents > 0)
    .sort((a, b) => b.expense_cents - a.expense_cents)
    .slice(0, 7)
    .map((group) => ({
      ...group,
      percent: total ? (group.expense_cents / total) * 100 : 0,
    }))
})

function itemDate(item) {
  return item.occurred_at
}

async function loadTransactions() {
  try {
    const params = {
      ...range.value,
      sort_by: 'occurred_at',
      sort_order: 'desc',
      limit: 200,
    }
    if (typeFilter.value !== 'all') params.type = typeFilter.value
    const result = await ledgerApi.list(params)
    transactions.value = result.items
  } catch (error) {
    toast.error(error.message)
  }
}

async function loadLedger() {
  loading.value = true
  try {
    const [summaryResult] = await Promise.all([
      ledgerApi.summary({ ...range.value, group_by: 'category' }),
      loadTransactions(),
    ])
    summary.value = summaryResult
  } catch (error) {
    toast.error(error.message)
  } finally {
    loading.value = false
  }
}

watch(currentMonth, loadLedger)
watch(typeFilter, loadTransactions)

function moveMonth(offset) {
  currentMonth.value = addMonths(currentMonth.value, offset)
}

function goCurrentMonth() {
  currentMonth.value = startOfMonth(new Date())
}

function resetForm() {
  form.type = typeFilter.value === 'income' ? 'income' : 'expense'
  form.amountYuan = ''
  form.category = ''
  form.note = ''
  form.occurredLocal = isoToLocalInput(new Date().toISOString())
}

function openCreate() {
  editing.value = null
  resetForm()
  formOpen.value = true
}

function openEdit(item) {
  editing.value = item
  form.type = item.type
  form.amountYuan = centsToYuanInput(item.amount_cents)
  form.category = item.category
  form.note = item.note || ''
  form.occurredLocal = isoToLocalInput(item.occurred_at)
  formOpen.value = true
}

async function saveTransaction() {
  const amountCents = yuanToCents(form.amountYuan)
  if (!amountCents) {
    toast.warning('请输入大于 0 的金额')
    return
  }
  if (!form.category.trim()) {
    toast.warning('请填写分类')
    return
  }

  saving.value = true
  const payload = {
    type: form.type,
    amount_cents: amountCents,
    category: form.category.trim(),
    note: form.note.trim() || null,
    occurred_at: localInputToIso(form.occurredLocal) || new Date().toISOString(),
  }

  try {
    if (editing.value) {
      await ledgerApi.update(editing.value.id, payload)
      toast.success('账目已更新')
    } else {
      await ledgerApi.create(payload)
      toast.success(form.type === 'income' ? '收入已记录' : '支出已记录')
    }
    formOpen.value = false
    await loadLedger()
  } catch (error) {
    toast.error(error.message)
  } finally {
    saving.value = false
  }
}

async function deleteTransaction(item) {
  const confirmed = await dialog.ask({
    title: '删除账目',
    message: `确定删除「${item.category} ${formatMoney(item.amount_cents)}」吗？`,
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  try {
    await ledgerApi.remove(item.id)
    toast.success('账目已删除')
    await loadLedger()
  } catch (error) {
    toast.error(error.message)
  }
}

onMounted(loadLedger)
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <PageHeader
        eyebrow="LEDGER"
        title="账本"
        description="看一看钱流向哪里，让每一笔支出都更接近你想要的生活。"
      >
        <template #actions>
          <div class="month-picker">
            <button class="icon-btn" type="button" title="上个月" @click="moveMonth(-1)">
              <ChevronLeft :size="16" />
            </button>
            <button class="month-label" type="button" @click="goCurrentMonth">
              {{ monthLabel }}
            </button>
            <button class="icon-btn" type="button" title="下个月" @click="moveMonth(1)">
              <ChevronRight :size="16" />
            </button>
          </div>
          <button class="btn btn-primary" type="button" @click="openCreate">
            <Plus :size="15" />
            记一笔
          </button>
        </template>
      </PageHeader>

      <section class="metrics-grid">
        <MetricCard
          label="本月收入"
          :value="loading ? '—' : formatMoney(summary?.income_cents || 0)"
          :hint="`${summary?.transaction_count || 0} 笔账目`"
          :icon="TrendingUp"
          tone="income"
        />
        <MetricCard
          label="本月支出"
          :value="loading ? '—' : formatMoney(summary?.expense_cents || 0)"
          hint="按分类查看支出结构"
          :icon="TrendingDown"
          tone="expense"
        />
        <MetricCard
          label="本月结余"
          :value="loading ? '—' : formatMoney(summary?.balance_cents || 0)"
          :hint="summary?.balance_cents >= 0 ? '保持得不错' : '本月支出高于收入'"
          :icon="Wallet"
          tone="accent"
        />
      </section>

      <section class="ledger-grid">
        <article class="card transactions-card">
          <header class="ledger-head">
            <div>
              <span class="eyebrow">CASH FLOW</span>
              <h2 class="section-title">
                <CircleDollarSign :size="17" />
                流水明细
              </h2>
            </div>
            <div class="segmented">
              <button
                type="button"
                :class="{ active: typeFilter === 'all' }"
                @click="typeFilter = 'all'"
              >
                全部
              </button>
              <button
                type="button"
                :class="{ active: typeFilter === 'expense' }"
                @click="typeFilter = 'expense'"
              >
                支出
              </button>
              <button
                type="button"
                :class="{ active: typeFilter === 'income' }"
                @click="typeFilter = 'income'"
              >
                收入
              </button>
            </div>
          </header>

          <div v-if="loading" class="loading-state">
            <span class="spinner"></span>
            正在核对本月流水
          </div>

          <EmptyState
            v-else-if="!transactions.length"
            title="本月还没有账目"
            description="记录第一笔，月末回看时会更了解自己的消费节奏。"
            :icon="Wallet"
          >
            <button class="btn btn-sm" type="button" @click="openCreate">
              <Plus :size="14" /> 记一笔
            </button>
          </EmptyState>

          <div v-else class="transaction-groups">
            <section
              v-for="group in groupedTransactions"
              :key="group.key"
              class="transaction-group"
            >
              <header class="day-header">
                <span>{{ group.label }}</span>
                <span class="day-totals">
                  <span v-if="group.income" class="money--income">+{{ formatMoney(group.income) }}</span>
                  <span v-if="group.expense" class="money--expense">-{{ formatMoney(group.expense) }}</span>
                </span>
              </header>

              <div class="transaction-list">
                <article
                  v-for="item in group.items"
                  :key="item.id"
                  class="transaction-item"
                  :style="toneStyle(item.category)"
                >
                  <span class="transaction-icon">
                    {{ item.category.slice(0, 1) }}
                  </span>
                  <div class="transaction-copy">
                    <div class="transaction-title-row">
                      <strong>{{ item.category }}</strong>
                      <span class="transaction-time">{{ formatTime(item.occurred_at) }}</span>
                    </div>
                    <p>{{ item.note || (item.type === 'income' ? '收入记录' : '支出记录') }}</p>
                  </div>
                  <strong
                    class="transaction-amount money"
                    :class="item.type === 'income' ? 'money--income' : 'money--expense'"
                  >
                    {{ item.type === 'income' ? '+' : '-' }}{{ formatMoney(item.amount_cents) }}
                  </strong>
                  <div class="transaction-actions">
                    <button class="icon-btn" type="button" title="编辑" @click="openEdit(item)">
                      <Pencil :size="14" />
                    </button>
                    <button
                      class="icon-btn icon-btn--danger"
                      type="button"
                      title="删除"
                      @click="deleteTransaction(item)"
                    >
                      <Trash2 :size="14" />
                    </button>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </article>

        <aside class="ledger-side">
          <article class="card category-card">
            <header class="ledger-head ledger-head--compact">
              <div>
                <span class="eyebrow">BREAKDOWN</span>
                <h2 class="section-title">支出构成</h2>
              </div>
              <span class="chip">{{ expenseGroups.length }} 类</span>
            </header>

            <div v-if="loading" class="loading-state loading-state--small">
              <span class="spinner"></span>
            </div>
            <EmptyState
              v-else-if="!expenseGroups.length"
              title="暂无支出数据"
              description="本月还没有支出记录。"
              :icon="TrendingDown"
            />
            <div v-else class="category-list">
              <div
                v-for="group in expenseGroups"
                :key="group.key"
                class="category-row"
                :style="toneStyle(group.key)"
              >
                <div class="category-row__head">
                  <span class="category-name">
                    <span class="category-swatch"></span>
                    {{ group.key }}
                  </span>
                  <span class="category-amount money">{{ formatMoney(group.expense_cents) }}</span>
                </div>
                <div class="category-bar">
                  <span
                    class="category-bar__fill"
                    :style="{ width: `${group.percent}%` }"
                  ></span>
                </div>
                <span class="category-percent">{{ group.percent.toFixed(1) }}%</span>
              </div>
            </div>
          </article>

          <article class="ledger-note card">
            <span class="ledger-note__icon"><Wallet :size="17" /></span>
            <div>
              <strong>本月结余</strong>
              <p>收入减去支出后的可支配余额。</p>
              <span class="money">{{ formatMoney(summary?.balance_cents || 0) }}</span>
            </div>
          </article>
        </aside>
      </section>
    </div>

    <Modal
      v-model="formOpen"
      :title="editing ? '编辑账目' : '记一笔'"
      subtitle="金额以元为单位，保存后按分存储，避免精度误差。"
      :width="500"
    >
      <form class="ledger-form" @submit.prevent="saveTransaction">
        <div class="type-switch">
          <button
            type="button"
            class="type-option type-option--expense"
            :class="{ active: form.type === 'expense' }"
            @click="form.type = 'expense'"
          >
            <TrendingDown :size="17" />
            支出
          </button>
          <button
            type="button"
            class="type-option type-option--income"
            :class="{ active: form.type === 'income' }"
            @click="form.type = 'income'"
          >
            <TrendingUp :size="17" />
            收入
          </button>
        </div>

        <div class="field">
          <label for="ledger-amount">金额</label>
          <div class="amount-input-wrap">
            <span>¥</span>
            <input
              id="ledger-amount"
              v-model="form.amountYuan"
              class="amount-input"
              type="number"
              min="0.01"
              step="0.01"
              inputmode="decimal"
              placeholder="0.00"
              autofocus
            />
          </div>
        </div>

        <div class="form-grid">
          <div class="field">
            <label for="ledger-category">分类</label>
            <input
              id="ledger-category"
              v-model="form.category"
              class="input"
              list="ledger-categories"
              maxlength="50"
              placeholder="例如：餐饮"
            />
            <datalist id="ledger-categories">
              <option v-for="category in categorySuggestions" :key="category" :value="category" />
            </datalist>
          </div>
          <div class="field">
            <label for="ledger-time">发生时间</label>
            <input
              id="ledger-time"
              v-model="form.occurredLocal"
              class="input"
              type="datetime-local"
            />
          </div>
        </div>

        <div class="field">
          <label for="ledger-note">备注</label>
          <textarea
            id="ledger-note"
            v-model="form.note"
            class="textarea ledger-note-input"
            maxlength="500"
            placeholder="这笔钱花在了什么上？"
          ></textarea>
        </div>

        <button class="form-submit-hidden" type="submit"></button>
      </form>

      <template #footer>
        <button class="btn" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="saving" @click="saveTransaction">
          <span v-if="saving" class="spinner spinner--small"></span>
          {{ editing ? '保存修改' : '保存账目' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.month-picker {
  display: flex;
  height: 38px;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--stroke);
  border-radius: 11px;
  background: rgba(4, 8, 13, 0.3);
}

.month-label {
  min-width: 104px;
  border: 0;
  border-radius: 8px;
  color: var(--text-2);
  background: transparent;
  font-size: 11.5px;
  font-weight: 580;
  cursor: pointer;
}

.month-label:hover {
  color: var(--text-1);
  background: rgba(255, 255, 255, 0.05);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.ledger-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.65fr);
  gap: 14px;
  margin-top: 14px;
}

.transactions-card {
  min-height: 520px;
  padding: 20px 20px 24px;
}

.ledger-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.ledger-head .section-title {
  margin-top: 5px;
}

.ledger-head--compact {
  margin-bottom: 12px;
}

.transaction-groups {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 4px 7px;
  color: var(--text-3);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.day-totals {
  display: flex;
  gap: 12px;
  font-variant-numeric: tabular-nums;
}

.transaction-list {
  display: flex;
  flex-direction: column;
}

.transaction-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 8px;
  border-bottom: 1px solid var(--stroke);
  border-radius: 9px;
  transition: background 150ms var(--ease-out);
}

.transaction-item:hover {
  background: rgba(255, 255, 255, 0.032);
}

.transaction-item:last-child {
  border-bottom-color: transparent;
}

.transaction-icon {
  display: grid;
  width: 37px;
  height: 37px;
  flex: none;
  place-items: center;
  border: 1px solid var(--tone-border);
  border-radius: 11px;
  color: var(--tone);
  background: var(--tone-bg);
  font-size: 13px;
  font-weight: 650;
}

.transaction-copy {
  min-width: 0;
  flex: 1;
}

.transaction-title-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.transaction-title-row strong {
  font-size: 12.5px;
  font-weight: 590;
}

.transaction-time {
  color: var(--text-3);
  font-size: 9.5px;
  font-variant-numeric: tabular-nums;
}

.transaction-copy p {
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 10.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.transaction-amount {
  flex: none;
  font-size: 13px;
  font-weight: 620;
}

.transaction-actions {
  display: flex;
  flex: none;
  opacity: 0;
  transition: opacity 150ms var(--ease-out);
}

.transaction-item:hover .transaction-actions,
.transaction-item:focus-within .transaction-actions {
  opacity: 1;
}

.ledger-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.category-card {
  padding: 18px 20px 22px;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 18px;
}

.category-row {
  position: relative;
}

.category-row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.category-name {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-2);
  font-size: 11.5px;
}

.category-swatch {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--tone);
  box-shadow: 0 0 8px var(--tone-glow);
}

.category-amount {
  color: var(--text-2);
  font-size: 10.5px;
}

.category-bar {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
}

.category-bar__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--tone), color-mix(in srgb, var(--tone) 48%, transparent));
  box-shadow: 0 0 10px var(--tone-glow);
  transition: width 450ms var(--ease-out);
}

.category-percent {
  position: absolute;
  right: 0;
  bottom: -14px;
  color: var(--text-3);
  font-size: 8.5px;
  opacity: 0;
  transition: opacity 150ms ease;
}

.category-row:hover .category-percent {
  opacity: 1;
}

.ledger-note {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 20px;
  border-color: color-mix(in srgb, var(--accent) 14%, var(--stroke));
  background:
    radial-gradient(300px 120px at 100% 0%, var(--accent-soft), transparent 70%),
    var(--surface-1);
}

.ledger-note__icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex: none;
  place-items: center;
  border-radius: 10px;
  color: var(--accent);
  background: var(--accent-soft);
}

.ledger-note strong {
  display: block;
  font-size: 12px;
  font-weight: 600;
}

.ledger-note p {
  margin-top: 3px;
  color: var(--text-3);
  font-size: 10.5px;
  line-height: 1.5;
}

.ledger-note > div > .money {
  display: block;
  margin-top: 10px;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.04em;
}

.ledger-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.type-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 4px;
  border: 1px solid var(--stroke);
  border-radius: 13px;
  background: rgba(4, 8, 13, 0.35);
}

.type-option {
  display: flex;
  height: 42px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: var(--text-3);
  background: transparent;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: 160ms var(--ease-out);
}

.type-option:hover {
  color: var(--text-1);
}

.type-option--expense.active {
  border-color: rgba(255, 130, 152, 0.22);
  color: var(--expense);
  background: rgba(255, 130, 152, 0.1);
}

.type-option--income.active {
  border-color: rgba(94, 226, 166, 0.22);
  color: var(--income);
  background: rgba(94, 226, 166, 0.1);
}

.amount-input-wrap {
  display: flex;
  height: 56px;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border: 1px solid var(--stroke-strong);
  border-radius: 13px;
  background: rgba(5, 9, 14, 0.5);
  transition: 160ms var(--ease-out);
}

.amount-input-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.amount-input-wrap > span {
  color: var(--text-3);
  font-family: var(--font-display);
  font-size: 21px;
}

.amount-input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: none;
  color: var(--text-1);
  background: transparent;
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 620;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.amount-input::placeholder {
  color: rgba(255, 255, 255, 0.16);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ledger-note-input {
  min-height: 86px;
}

.form-submit-hidden {
  display: none;
}

.spinner--small {
  width: 13px;
  height: 13px;
  border-width: 1.5px;
}

.loading-state--small {
  min-height: 100px;
}

@media (max-width: 1160px) {
  .ledger-grid {
    grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  }
}

@media (max-width: 960px) {
  .ledger-grid {
    grid-template-columns: 1fr;
  }

  .ledger-side {
    display: grid;
    grid-template-columns: 1fr 0.7fr;
  }
}

@media (max-width: 720px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .ledger-side {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .transaction-actions {
    opacity: 1;
  }
}
</style>
