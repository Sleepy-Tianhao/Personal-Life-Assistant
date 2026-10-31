<script setup>
import {
  Check,
  Database,
  ExternalLink,
  Info,
  Palette,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Wifi,
  WifiOff,
} from '@lucide/vue'
import { computed, ref } from 'vue'

import { getServiceInfo, getApiBaseUrl, setApiBaseUrl } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import { useAppStore } from '@/stores/app'
import { useToastStore } from '@/stores/toast'
import { ACCENTS, applyAccent, getStoredAccent } from '@/utils/theme'

const appStore = useAppStore()
const toast = useToastStore()

const apiBase = ref(getApiBaseUrl())
const accent = ref(getStoredAccent())
const testing = ref(false)
const serviceInfo = computed(() => appStore.serviceInfo)

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
            界面采用 ClassIsland 风格的 Fluent 深色玻璃、导航栏与悬浮信息岛，
            同时针对个人生活助理的使用场景重新设计了内容布局。
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
            界面设计参考 ClassIsland 的 Fluent 深色视觉语言与悬浮信息岛概念，
            代码、组件与品牌素材均为本项目的独立实现。
          </p>
        </section>
      </div>
    </div>
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
  color: var(--accent);
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
  border-color: rgba(94, 226, 166, 0.18);
  color: var(--success);
  background: var(--success-soft);
}

.connection-status--offline {
  border-color: rgba(255, 112, 137, 0.18);
  color: var(--danger);
  background: var(--danger-soft);
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
  background: rgba(255, 255, 255, 0.04);
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
  color: var(--accent);
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
  background:
    radial-gradient(240px 80px at 50% 0%, var(--accent-faint), transparent 70%),
    rgba(4, 8, 13, 0.28);
}

.preview-island {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--stroke-strong);
  border-radius: 999px;
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.42);
  font-size: 8.5px;
}

.preview-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent-glow);
}

.preview-chip {
  padding: 3px 7px;
  border-radius: 5px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 8px;
}

.preview-btn {
  padding: 4px 8px;
  border-radius: 6px;
  color: #04111d;
  background: var(--accent);
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
  background: rgba(255, 255, 255, 0.022);
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
  color: var(--accent);
  font-size: 9.5px;
}

.doc-links a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
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
  background: rgba(255, 255, 255, 0.045);
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
  background: rgba(255, 255, 255, 0.055);
  font-family: var(--font-mono);
  font-size: 9px;
}

.about-section {
  grid-column: 1 / -1;
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
  border: 1px solid var(--stroke-accent);
  border-radius: 17px;
  color: #04111d;
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  box-shadow: 0 14px 35px var(--accent-glow);
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

  .about-section {
    grid-column: auto;
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
