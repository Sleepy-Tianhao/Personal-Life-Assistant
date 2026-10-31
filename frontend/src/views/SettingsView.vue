<script setup>
import {
  ArrowDown,
  ArrowUp,
  Check,
  Database,
  ExternalLink,
  GripVertical,
  Info,
  LayoutGrid,
  Lock,
  Palette,
  PanelTop,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Trash2,
  Unlock,
  Wifi,
  WifiOff,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { getServiceInfo, getApiBaseUrl, setApiBaseUrl } from '@/api/http'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import {
  BLOCK_TYPES,
  DEFAULT_BLOCKS,
  MAX_FLOATING_BLOCKS,
  MIN_FLOATING_BLOCKS,
  blockMeta,
  cloneBlocks,
  createBlock,
  normalizeBlocks,
} from '@/floating/boardConfig'
import { useAppStore } from '@/stores/app'
import { useToastStore } from '@/stores/toast'
import { ACCENTS, applyAccent, getStoredAccent } from '@/utils/theme'

const appStore = useAppStore()
const toast = useToastStore()
const floatingBridge = window.desktop?.floating || null

const apiBase = ref(getApiBaseUrl())
const accent = ref(getStoredAccent())
const testing = ref(false)
const serviceInfo = computed(() => appStore.serviceInfo)

const floatingAvailable = Boolean(floatingBridge)
const floatingState = ref({
  enabled: false,
  locked: false,
  blocks: cloneBlocks(DEFAULT_BLOCKS),
})
const floatingBusy = ref(false)
const floatingEditorOpen = ref(false)
const floatingDraft = ref(cloneBlocks(DEFAULT_BLOCKS))
const newFloatingType = ref('clock')
let unsubscribeFloating = null

const floatingStatus = computed(() => {
  if (!floatingAvailable) return '仅桌面应用可用'
  if (!floatingState.value.enabled) return '浮窗已关闭'
  return floatingState.value.locked ? '浮窗运行中 · 已锁定' : '浮窗运行中'
})

const floatingPreviewBlocks = computed(() =>
  floatingState.value.blocks.map((block) => blockMeta(block.type)),
)

const floatingDraftCount = computed(() => floatingDraft.value.length)

const serviceBase = computed(() => {
  try {
    const url = new URL(apiBase.value)
    url.pathname = url.pathname.replace(/\/api\/v1\/?$/, '')
    return url.toString().replace(/\/+$/, '')
  } catch {
    return apiBase.value
  }
})

const statusLabel = computed(() => {
  if (appStore.backendStatus === 'checking') return '正在检查连接'
  return appStore.backendOnline ? '服务正常' : '无法连接'
})

const statusClass = computed(() => {
  if (appStore.backendStatus === 'checking') return 'checking'
  return appStore.backendOnline ? 'online' : 'offline'
})

function chooseAccent(item) {
  accent.value = applyAccent(item.id)
  toast.success(`已切换为${item.label}`)
}

async function saveAndTest() {
  const trimmed = apiBase.value.trim()
  if (!/^https?:\/\//i.test(trimmed)) {
    toast.warning('API 地址需要以 http:// 或 https:// 开头')
    return
  }
  setApiBaseUrl(trimmed)
  apiBase.value = getApiBaseUrl()
  appStore.$patch({ serviceInfo: null, backendStatus: 'checking' })
  testing.value = true
  try {
    const online = await appStore.refreshHealth()
    if (online) {
      appStore.$patch({ serviceInfo: await getServiceInfo() })
      toast.success('后端连接成功')
    } else {
      toast.error('无法连接后端，请确认 FastAPI 已启动')
    }
  } catch (error) {
    toast.error(error.message || '连接测试失败')
  } finally {
    testing.value = false
  }
}

function resetApiBase() {
  apiBase.value = 'http://127.0.0.1:8000/api/v1'
}

function applyFloatingState(state) {
  if (!state) return
  floatingState.value = {
    enabled: Boolean(state.enabled),
    locked: Boolean(state.locked),
    blocks: normalizeBlocks(state.blocks),
  }
}

async function toggleFloating() {
  if (!floatingBridge) {
    toast.warning('桌面浮窗仅可在 Electron 桌面应用中使用')
    return
  }
  floatingBusy.value = true
  try {
    const state = await floatingBridge.setEnabled(!floatingState.value.enabled)
    applyFloatingState(state)
    toast.success(state.enabled ? '桌面浮窗已开启' : '桌面浮窗已隐藏')
  } catch (error) {
    toast.error(error.message || '无法切换桌面浮窗')
  } finally {
    floatingBusy.value = false
  }
}

async function toggleFloatingLock() {
  if (!floatingBridge) return
  floatingBusy.value = true
  try {
    const state = await floatingBridge.setLocked(!floatingState.value.locked)
    applyFloatingState(state)
    toast.success(state.locked ? '浮窗位置已锁定' : '浮窗已解锁，可以拖动')
  } catch (error) {
    toast.error(error.message || '无法切换浮窗锁定状态')
  } finally {
    floatingBusy.value = false
  }
}

function openFloatingEditor() {
  if (!floatingAvailable) {
    toast.warning('请使用 Electron 桌面应用配置浮窗')
    return
  }
  floatingDraft.value = cloneBlocks(floatingState.value.blocks)
  newFloatingType.value = 'clock'
  floatingEditorOpen.value = true
}

function addFloatingBlock() {
  if (floatingDraft.value.length >= MAX_FLOATING_BLOCKS) {
    toast.warning(`最多添加 ${MAX_FLOATING_BLOCKS} 个板块`)
    return
  }
  floatingDraft.value.push(createBlock(newFloatingType.value))
}

function removeFloatingBlock(index) {
  if (floatingDraft.value.length <= MIN_FLOATING_BLOCKS) {
    toast.warning('至少保留一个板块')
    return
  }
  floatingDraft.value.splice(index, 1)
}

function moveFloatingBlock(index, direction) {
  const target = index + direction
  if (target < 0 || target >= floatingDraft.value.length) return
  const [block] = floatingDraft.value.splice(index, 1)
  floatingDraft.value.splice(target, 0, block)
}

async function saveFloatingBlocks() {
  if (!floatingBridge) return
  floatingBusy.value = true
  try {
    const state = await floatingBridge.updateBlocks(normalizeBlocks(floatingDraft.value))
    applyFloatingState(state)
    floatingEditorOpen.value = false
    toast.success('浮窗板块已更新')
  } catch (error) {
    toast.error(error.message || '无法保存浮窗板块')
  } finally {
    floatingBusy.value = false
  }
}

onMounted(async () => {
  if (!floatingBridge) return
  try {
    applyFloatingState(await floatingBridge.getState())
    unsubscribeFloating = floatingBridge.onStateChanged(applyFloatingState)
  } catch {
    toast.error('无法读取桌面浮窗状态')
  }
})

onBeforeUnmount(() => {
  unsubscribeFloating?.()
})
</script>

<template>
  <div class="page">
    <div class="page-inner settings-page">
      <PageHeader
        eyebrow="SETTINGS"
        title="设置"
        description="连接后端服务，调整界面强调色，查看这个桌面工作台的基本信息。"
      />

      <div class="settings-grid">
        <section class="settings-section card">
          <header class="settings-section__head">
            <span class="settings-icon"><Palette :size="18" /></span>
            <div>
              <h2>外观</h2>
              <p>选择适合你的强调色，界面会立即更新。</p>
            </div>
          </header>

          <div class="accent-options">
            <button
              v-for="item in ACCENTS"
              :key="item.id"
              class="accent-option"
              :class="{ 'accent-option--active': accent === item.id }"
              type="button"
              @click="chooseAccent(item)"
            >
              <span
                class="accent-swatch"
                :style="{
                  background: item.color,
                  boxShadow: `0 0 24px ${item.color}55`,
                }"
              ></span>
              <span class="accent-copy">
                <strong>{{ item.label }}</strong>
                <small>{{ item.color.toUpperCase() }}</small>
              </span>
              <Check v-if="accent === item.id" :size="14" class="accent-check" />
            </button>
          </div>

          <div class="appearance-preview">
            <span class="preview-island">
              <span class="preview-dot"></span>
              12:30 · 正在上课 · 数据结构
            </span>
            <span class="preview-chip">今日课表</span>
            <span class="preview-btn">主按钮</span>
          </div>

          <p class="settings-note">
            界面保留了 ClassIsland 式导航栏与悬浮信息岛的结构，但改为浅色、扁平、
            低饱和的清新配色，让每天的使用更轻盈。
          </p>
        </section>

        <section class="settings-section card">
          <header class="settings-section__head">
            <span class="settings-icon"><Server :size="18" /></span>
            <div>
              <h2>后端连接</h2>
              <p>FastAPI 服务默认运行在 127.0.0.1:8000。</p>
            </div>
            <span class="connection-status" :class="`connection-status--${statusClass}`">
              <Wifi v-if="appStore.backendOnline" :size="13" />
              <WifiOff v-else :size="13" />
              {{ statusLabel }}
            </span>
          </header>

          <div class="field">
            <label for="api-base">API Base URL</label>
            <input
              id="api-base"
              v-model="apiBase"
              class="input mono"
              spellcheck="false"
              placeholder="http://127.0.0.1:8000/api/v1"
            />
            <span class="field-hint">
              必须包含 <code>/api/v1</code>。修改后点击“保存并测试”。
            </span>
          </div>

          <div class="settings-actions">
            <button class="btn btn-sm" type="button" @click="resetApiBase">
              <RefreshCw :size="13" />
              恢复默认
            </button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="testing" @click="saveAndTest">
              <span v-if="testing" class="spinner spinner--small"></span>
              {{ testing ? '正在测试' : '保存并测试' }}
            </button>
          </div>

          <div class="service-info">
            <div>
              <span>服务</span>
              <strong>{{ serviceInfo?.name || 'FastAPI · Personal Life Assistant' }}</strong>
            </div>
            <div>
              <span>版本</span>
              <strong>{{ serviceInfo?.version || appStore.serviceInfo?.version || '—' }}</strong>
            </div>
          </div>

          <div class="doc-links">
            <a :href="`${serviceBase}/docs`" target="_blank" rel="noreferrer">
              Swagger UI
              <ExternalLink :size="12" />
            </a>
            <a :href="`${serviceBase}/redoc`" target="_blank" rel="noreferrer">
              ReDoc
              <ExternalLink :size="12" />
            </a>
            <a :href="`${serviceBase}/openapi.json`" target="_blank" rel="noreferrer">
              OpenAPI
              <ExternalLink :size="12" />
            </a>
          </div>
        </section>

        <section class="settings-section card floating-section">
          <header class="settings-section__head">
            <span class="settings-icon"><PanelTop :size="18" /></span>
            <div>
              <h2>桌面浮窗</h2>
              <p>像 ClassIsland 一样，把关键信息常驻在桌面最上层。</p>
            </div>
            <span
              class="connection-status"
              :class="{
                'connection-status--online': floatingAvailable && floatingState.enabled,
                'connection-status--warning': !floatingAvailable,
              }"
            >
              {{ floatingStatus }}
            </span>
          </header>

          <div class="floating-layout">
            <div class="floating-main">
              <div class="floating-board-preview">
                <span class="floating-preview-brand">L</span>
                <span class="floating-preview-divider"></span>
                <span
                  v-for="(block, index) in floatingPreviewBlocks"
                  :key="`${block.type}-${index}`"
                  class="floating-preview-block"
                >
                  <LayoutGrid :size="11" />
                  {{ block.label }}
                </span>
                <span class="floating-preview-grip">⋮⋮</span>
              </div>
              <p class="floating-description">
                浮窗始终置顶，可拖动到桌面任意位置。锁定后避免误移动；板块内容会随数据自动更新。
              </p>
            </div>

            <div class="floating-controls">
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="!floatingAvailable || floatingBusy"
                @click="toggleFloating"
              >
                <span v-if="floatingBusy" class="spinner spinner--small"></span>
                <PanelTop v-else :size="14" />
                {{ floatingState.enabled ? '隐藏浮窗' : '显示浮窗' }}
              </button>
              <button
                class="btn btn-sm"
                type="button"
                :disabled="!floatingAvailable || !floatingState.enabled || floatingBusy"
                @click="toggleFloatingLock"
              >
                <Lock v-if="floatingState.locked" :size="14" />
                <Unlock v-else :size="14" />
                {{ floatingState.locked ? '解锁位置' : '锁定位置' }}
              </button>
              <button
                class="btn btn-sm"
                type="button"
                :disabled="!floatingAvailable"
                @click="openFloatingEditor"
              >
                <LayoutGrid :size="14" />
                编辑板块
              </button>
            </div>
          </div>

          <div class="floating-meta">
            <span class="chip">{{ floatingState.blocks.length }} / {{ MAX_FLOATING_BLOCKS }} 个板块</span>
            <span class="chip">最多 8 个板块</span>
            <span v-if="!floatingAvailable" class="chip chip--warning">
              当前为浏览器预览，请在 Electron 中使用
            </span>
            <span v-else class="chip chip--accent">
              Linux / Windows 桌面可用
            </span>
          </div>
        </section>

        <section class="settings-section card">
          <header class="settings-section__head">
            <span class="settings-icon"><ShieldCheck :size="18" /></span>
            <div>
              <h2>本地与隐私</h2>
              <p>所有数据保存在本机，不经过云端服务。</p>
            </div>
          </header>

          <div class="privacy-list">
            <div class="privacy-row">
              <span class="privacy-icon"><Database :size="16" /></span>
              <div>
                <strong>SQLite 本地数据库</strong>
                <p>待办、账目、日程、课表和日记均存储在后端 data 目录中。</p>
              </div>
            </div>
            <div class="privacy-row">
              <span class="privacy-icon"><ShieldCheck :size="16" /></span>
              <div>
                <strong>单用户、无账号</strong>
                <p>后端只监听本机地址，不包含登录和云同步机制。</p>
              </div>
            </div>
            <div class="privacy-row">
              <span class="privacy-icon"><Info :size="16" /></span>
              <div>
                <strong>备份建议</strong>
                <p>定期备份 <code>backend/data/life_assistant.db</code> 即可保存全部数据。</p>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section card about-section">
          <header class="settings-section__head">
            <span class="settings-icon"><Sparkles :size="18" /></span>
            <div>
              <h2>关于</h2>
              <p>Personal Life Assistant Desktop</p>
            </div>
            <span class="version-badge">v0.1.0</span>
          </header>

          <div class="about-brand">
            <div class="about-mark">L</div>
            <div>
              <strong>Life Assistant</strong>
              <p>把待办、时间、课程、收支与日记放在同一个安静的桌面空间里。</p>
            </div>
          </div>

          <div class="tech-row">
            <span class="chip">Vue 3</span>
            <span class="chip">Vite</span>
            <span class="chip">Electron</span>
            <span class="chip">FastAPI</span>
            <span class="chip">SQLite</span>
          </div>

          <p class="settings-note about-note">
            导航结构与悬浮信息岛的思路参考 ClassIsland，并以浅色扁平、清新纯色重新设计；
            代码、组件与品牌素材均为本项目的独立实现。
          </p>
        </section>
      </div>
    </div>

    <Modal
      v-model="floatingEditorOpen"
      title="编辑桌面浮窗"
      subtitle="选择板块内容并调整顺序。修改会立即同步到桌面浮窗。"
      :width="660"
    >
      <div class="floating-editor">
        <div class="floating-editor__meta">
          <span>板块数量</span>
          <strong>{{ floatingDraftCount }} / {{ MAX_FLOATING_BLOCKS }}</strong>
        </div>

        <div class="block-editor-list">
          <div
            v-for="(block, index) in floatingDraft"
            :key="block.id"
            class="block-editor-row"
          >
            <span class="block-editor-order">
              <GripVertical :size="14" />
              {{ index + 1 }}
            </span>

            <div class="block-editor-fields">
              <select v-model="block.type" class="select" aria-label="板块内容">
                <option v-for="type in BLOCK_TYPES" :key="type.type" :value="type.type">
                  {{ type.label }}
                </option>
              </select>
              <span class="block-editor-description">{{ blockMeta(block.type).description }}</span>
              <input
                v-if="block.type === 'custom'"
                v-model="block.text"
                class="input block-editor-text"
                maxlength="80"
                placeholder="输入要显示的便签文字"
                aria-label="自定义文字"
              />
            </div>

            <div class="block-editor-actions">
              <button
                class="icon-btn"
                type="button"
                title="上移"
                :disabled="index === 0"
                @click="moveFloatingBlock(index, -1)"
              >
                <ArrowUp :size="14" />
              </button>
              <button
                class="icon-btn"
                type="button"
                title="下移"
                :disabled="index === floatingDraft.length - 1"
                @click="moveFloatingBlock(index, 1)"
              >
                <ArrowDown :size="14" />
              </button>
              <button
                class="icon-btn icon-btn--danger"
                type="button"
                title="删除板块"
                :disabled="floatingDraft.length <= MIN_FLOATING_BLOCKS"
                @click="removeFloatingBlock(index)"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>

        <div class="block-add-row">
          <select v-model="newFloatingType" class="select" aria-label="新增板块类型">
            <option v-for="type in BLOCK_TYPES" :key="type.type" :value="type.type">
              {{ type.label }} · {{ type.description }}
            </option>
          </select>
          <button
            class="btn btn-sm"
            type="button"
            :disabled="floatingDraft.length >= MAX_FLOATING_BLOCKS"
            @click="addFloatingBlock"
          >
            <Plus :size="14" />
            添加板块
          </button>
        </div>
      </div>

      <template #footer>
        <button class="btn" type="button" @click="floatingEditorOpen = false">取消</button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="floatingBusy"
          @click="saveFloatingBlocks"
        >
          <span v-if="floatingBusy" class="spinner spinner--small"></span>
          保存板块
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 1160px;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: start;
}

.settings-section {
  padding: 20px;
}

.settings-section__head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.settings-icon {
  display: grid;
  width: 37px;
  height: 37px;
  flex: none;
  place-items: center;
  border: 1px solid var(--stroke-accent);
  border-radius: 11px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.settings-section__head > div {
  min-width: 0;
  flex: 1;
}

.settings-section__head h2 {
  color: var(--text-1);
  font-size: 14px;
  font-weight: 640;
  letter-spacing: -0.015em;
}

.settings-section__head p {
  margin-top: 3px;
  color: var(--text-3);
  font-size: 10.5px;
  line-height: 1.5;
}

.connection-status {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-3);
  font-size: 9.5px;
  white-space: nowrap;
}

.connection-status--online {
  border-color: color-mix(in srgb, var(--success) 18%, white);
  color: var(--success);
  background: var(--success-soft);
}

.connection-status--offline {
  border-color: color-mix(in srgb, var(--danger) 18%, white);
  color: var(--danger);
  background: var(--danger-soft);
}

.connection-status--warning {
  border-color: color-mix(in srgb, var(--warning) 20%, white);
  color: var(--warning);
  background: var(--warning-soft);
}

.accent-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
}

.accent-option {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border: 1px solid var(--stroke);
  border-radius: 11px;
  color: var(--text-2);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms var(--ease-out),
    background 160ms var(--ease-out);
}

.accent-option:hover,
.accent-option--active {
  border-color: var(--stroke-strong);
  background: var(--surface-2);
}

.accent-option--active {
  border-color: var(--stroke-accent);
  background: var(--accent-faint);
}

.accent-swatch {
  width: 22px;
  height: 22px;
  flex: none;
  border-radius: 7px;
}

.accent-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.accent-copy strong {
  font-size: 10.5px;
  font-weight: 600;
}

.accent-copy small {
  margin-top: 1px;
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 7.5px;
}

.accent-check {
  flex: none;
  color: var(--accent-deep);
}

.appearance-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 17px;
  padding: 14px;
  border: 1px solid var(--stroke);
  border-radius: 12px;
  background: var(--surface-2);
}

.preview-island {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-2);
  background: var(--surface-1);
  font-size: 8.5px;
}

.preview-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.preview-chip {
  padding: 3px 7px;
  border-radius: 5px;
  color: var(--accent-deep);
  background: var(--accent-soft);
  font-size: 8px;
}

.preview-btn {
  padding: 4px 8px;
  border-radius: 6px;
  color: #ffffff;
  background: var(--accent-strong);
  font-size: 8px;
  font-weight: 650;
}

.settings-note {
  margin-top: 14px;
  color: var(--text-3);
  font-size: 9.5px;
  line-height: 1.65;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.service-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 17px;
}

.service-info > div {
  padding: 9px 10px;
  border: 1px solid var(--stroke);
  border-radius: 9px;
  background: var(--surface-2);
}

.service-info span {
  display: block;
  color: var(--text-3);
  font-size: 8.5px;
}

.service-info strong {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-2);
  font-size: 10px;
  font-weight: 560;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-links {
  display: flex;
  flex-wrap: wrap;
  gap: 13px;
  margin-top: 16px;
  padding-top: 13px;
  border-top: 1px solid var(--stroke);
}

.doc-links a {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--accent-deep);
  font-size: 9.5px;
}

.doc-links a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.floating-section {
  grid-column: 1 / -1;
}

.floating-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.floating-main {
  min-width: 0;
  flex: 1;
}

.floating-board-preview {
  display: flex;
  align-items: center;
  width: max-content;
  max-width: 100%;
  min-height: 48px;
  gap: 0;
  padding: 6px 10px;
  overflow: hidden;
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--surface-2);
}

.floating-preview-brand {
  display: grid;
  width: 25px;
  height: 25px;
  flex: none;
  margin-right: 8px;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: var(--accent-strong);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
}

.floating-preview-divider {
  width: 1px;
  height: 22px;
  margin-right: 6px;
  background: var(--stroke);
}

.floating-preview-block {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
  color: var(--text-2);
  font-size: 9.5px;
  white-space: nowrap;
}

.floating-preview-block + .floating-preview-block {
  border-left: 1px solid var(--stroke);
}

.floating-preview-grip {
  margin-left: 4px;
  color: var(--text-3);
  font-size: 12px;
  letter-spacing: -2px;
}

.floating-description {
  max-width: 670px;
  margin-top: 9px;
  color: var(--text-3);
  font-size: 10px;
  line-height: 1.6;
}

.floating-controls {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
  max-width: 330px;
}

.floating-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--stroke);
}

.floating-editor {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.floating-editor__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-3);
  font-size: 10px;
}

.floating-editor__meta strong {
  color: var(--text-2);
  font-size: 11px;
  font-weight: 600;
}

.block-editor-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.block-editor-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--stroke);
  border-radius: 12px;
  background: var(--surface-2);
}

.block-editor-order {
  display: flex;
  width: 34px;
  flex: none;
  align-items: center;
  gap: 3px;
  padding-top: 10px;
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 9px;
}

.block-editor-fields {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.block-editor-fields .select {
  height: 34px;
  font-size: 11.5px;
  background-position:
    calc(100% - 16px) 14px,
    calc(100% - 11px) 14px;
}

.block-editor-description {
  color: var(--text-3);
  font-size: 9px;
  line-height: 1.4;
}

.block-editor-text {
  height: 34px;
  margin-top: 2px;
  font-size: 11.5px;
}

.block-editor-actions {
  display: flex;
  flex: none;
  gap: 1px;
  padding-top: 2px;
}

.block-editor-actions .icon-btn {
  width: 29px;
  height: 29px;
}

.block-add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

.block-add-row .select {
  min-width: 0;
  flex: 1;
  height: 36px;
  font-size: 11px;
  background-position:
    calc(100% - 16px) 15px,
    calc(100% - 11px) 15px;
}

.privacy-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.privacy-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.privacy-icon {
  display: grid;
  width: 30px;
  height: 30px;
  flex: none;
  place-items: center;
  border-radius: 9px;
  color: var(--text-2);
  background: var(--surface-2);
}

.privacy-row strong {
  display: block;
  color: var(--text-2);
  font-size: 10.5px;
  font-weight: 600;
}

.privacy-row p {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 9.5px;
  line-height: 1.55;
}

code {
  padding: 1px 4px;
  border-radius: 4px;
  color: var(--text-2);
  background: var(--surface-3);
  font-family: var(--font-mono);
  font-size: 9px;
}

.about-section {
  grid-column: auto;
}

.version-badge {
  padding: 4px 8px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 9px;
}

.about-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.about-mark {
  display: grid;
  width: 54px;
  height: 54px;
  flex: none;
  place-items: center;
  border: 1px solid var(--accent-strong);
  border-radius: 17px;
  color: #ffffff;
  background: var(--accent-strong);
  font-family: var(--font-display);
  font-size: 25px;
  font-weight: 760;
}

.about-brand strong {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.about-brand p {
  max-width: 520px;
  margin-top: 3px;
  color: var(--text-3);
  font-size: 10px;
  line-height: 1.55;
}

.tech-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 18px;
}

.about-note {
  padding-top: 13px;
  border-top: 1px solid var(--stroke);
}

.spinner--small {
  width: 12px;
  height: 12px;
  border-width: 1.5px;
}

@media (max-width: 980px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .floating-section {
    grid-column: auto;
  }

  .floating-layout {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .floating-controls {
    justify-content: flex-start;
    max-width: none;
  }
}

@media (max-width: 540px) {
  .accent-options {
    grid-template-columns: 1fr;
  }

  .settings-section__head {
    flex-wrap: wrap;
  }
}
</style>
