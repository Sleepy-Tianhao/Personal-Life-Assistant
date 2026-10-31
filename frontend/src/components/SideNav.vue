<script setup>
import {
  BookOpen,
  CalendarDays,
  GraduationCap,
  LayoutDashboard,
  ListTodo,
  Settings2,
  Wallet,
  Wifi,
  WifiOff,
} from '@lucide/vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()

const primaryItems = [
  { to: '/', label: '今日', icon: LayoutDashboard, description: '生活总览' },
  { to: '/todos', label: '待办', icon: ListTodo, description: '任务清单' },
  { to: '/schedule', label: '日程', icon: CalendarDays, description: '时间安排' },
  { to: '/timetable', label: '课表', icon: GraduationCap, description: '课程看板' },
]

const recordItems = [
  { to: '/ledger', label: '账本', icon: Wallet, description: '收支记录' },
  { to: '/diary', label: '日记', icon: BookOpen, description: '心情随笔' },
]

const backendLabel = computed(() => {
  if (appStore.backendStatus === 'checking') return '连接中'
  return appStore.backendOnline ? '后端已连接' : '后端离线'
})

function isActive(path) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>

<template>
  <aside class="side-nav">
    <div class="nav-intro">
      <span class="nav-intro__eyebrow">WORKSPACE</span>
      <span class="nav-intro__title">我的生活</span>
    </div>

    <nav class="nav-groups">
      <div class="nav-group">
        <span class="nav-group__label">生活</span>
        <RouterLink
          v-for="item in primaryItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ 'nav-item--active': isActive(item.to) }"
          :title="item.label"
        >
          <span class="nav-item__icon">
            <component :is="item.icon" :size="18" :stroke-width="1.8" />
          </span>
          <span class="nav-item__copy">
            <span class="nav-item__label">{{ item.label }}</span>
            <span class="nav-item__desc">{{ item.description }}</span>
          </span>
          <span class="nav-item__marker"></span>
        </RouterLink>
      </div>

      <div class="nav-group">
        <span class="nav-group__label">记录</span>
        <RouterLink
          v-for="item in recordItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ 'nav-item--active': isActive(item.to) }"
          :title="item.label"
        >
          <span class="nav-item__icon">
            <component :is="item.icon" :size="18" :stroke-width="1.8" />
          </span>
          <span class="nav-item__copy">
            <span class="nav-item__label">{{ item.label }}</span>
            <span class="nav-item__desc">{{ item.description }}</span>
          </span>
          <span class="nav-item__marker"></span>
        </RouterLink>
      </div>
    </nav>

    <div class="nav-footer">
      <RouterLink
        to="/settings"
        class="nav-item nav-item--settings"
        :class="{ 'nav-item--active': isActive('/settings') }"
        title="设置"
      >
        <span class="nav-item__icon">
          <Settings2 :size="18" :stroke-width="1.8" />
        </span>
        <span class="nav-item__copy">
          <span class="nav-item__label">设置</span>
          <span class="nav-item__desc">连接与外观</span>
        </span>
      </RouterLink>

      <RouterLink to="/settings" class="backend-card" title="打开连接设置">
        <span
          class="backend-card__dot"
          :class="{
            'backend-card__dot--online': appStore.backendOnline,
            'backend-card__dot--offline':
              appStore.backendStatus === 'offline',
          }"
        ></span>
        <span class="backend-card__copy">
          <span>{{ backendLabel }}</span>
          <small>FastAPI · SQLite</small>
        </span>
        <Wifi
          v-if="appStore.backendOnline"
          :size="14"
          class="backend-card__icon"
        />
        <WifiOff v-else :size="14" class="backend-card__icon" />
      </RouterLink>
    </div>
  </aside>
</template>

<style scoped>
.side-nav {
  display: flex;
  width: var(--sidebar-width);
  flex: none;
  flex-direction: column;
  min-height: 0;
  padding: 14px 12px 16px;
  transition: width 240ms var(--ease-out);
}

.nav-intro {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px 22px;
}

.nav-intro__eyebrow {
  color: var(--text-3);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.nav-intro__title {
  color: var(--text-1);
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.nav-groups {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.nav-group__label {
  padding: 0 12px 7px;
  color: var(--text-3);
  font-size: 9.5px;
  font-weight: 680;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.nav-item {
  position: relative;
  display: flex;
  min-height: 48px;
  align-items: center;
  gap: 11px;
  padding: 7px 11px;
  border: 1px solid transparent;
  border-radius: 13px;
  color: var(--text-2);
  transition:
    color 160ms var(--ease-out),
    background 160ms var(--ease-out),
    border-color 160ms var(--ease-out),
    transform 160ms var(--ease-out);
}

.nav-item:hover {
  color: var(--text-1);
  background: rgba(255, 255, 255, 0.045);
}

.nav-item:active {
  transform: scale(0.99);
}

.nav-item--active {
  border-color: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--text-1);
  background:
    linear-gradient(90deg, var(--accent-soft), transparent 90%),
    rgba(255, 255, 255, 0.035);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.nav-item__icon {
  display: grid;
  width: 32px;
  height: 32px;
  flex: none;
  place-items: center;
  border-radius: 9px;
  color: var(--text-3);
  background: rgba(255, 255, 255, 0.035);
  transition: 160ms var(--ease-out);
}

.nav-item--active .nav-item__icon {
  color: var(--accent);
  background: var(--accent-soft);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 15%, transparent);
}

.nav-item__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.22;
}

.nav-item__label {
  font-size: 13px;
  font-weight: 600;
}

.nav-item__desc {
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 9.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-item__marker {
  position: absolute;
  right: -1px;
  width: 3px;
  height: 18px;
  border-radius: 4px 0 0 4px;
  background: transparent;
  transition: background 160ms var(--ease-out);
}

.nav-item--active .nav-item__marker {
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent-glow);
}

.nav-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  padding-top: 20px;
}

.nav-item--settings {
  min-height: 42px;
}

.backend-card {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 9px;
  margin: 2px 4px 0;
  padding: 10px 11px;
  border: 1px solid var(--stroke);
  border-radius: 12px;
  background: rgba(4, 8, 13, 0.34);
  transition:
    border-color 160ms var(--ease-out),
    background 160ms var(--ease-out);
}

.backend-card:hover {
  border-color: var(--stroke-strong);
  background: rgba(255, 255, 255, 0.035);
}

.backend-card__dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: var(--warning);
  box-shadow: 0 0 9px rgba(244, 201, 106, 0.4);
}

.backend-card__dot--online {
  background: var(--success);
  box-shadow: 0 0 9px rgba(94, 226, 166, 0.45);
}

.backend-card__dot--offline {
  background: var(--danger);
  box-shadow: 0 0 9px rgba(255, 112, 137, 0.4);
}

.backend-card__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  color: var(--text-2);
  font-size: 10.5px;
  line-height: 1.25;
}

.backend-card__copy small {
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-3);
  font-size: 8.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.backend-card__icon {
  flex: none;
  color: var(--text-3);
}

@media (max-width: 1120px) {
  .side-nav {
    width: 72px;
    align-items: center;
    padding-inline: 8px;
  }

  .nav-intro {
    width: 100%;
    padding: 8px 0 19px;
    text-align: center;
  }

  .nav-intro__eyebrow,
  .nav-intro__title,
  .nav-group__label,
  .nav-item__copy,
  .backend-card__copy,
  .backend-card__icon {
    display: none;
  }

  .nav-groups {
    width: 100%;
    gap: 14px;
  }

  .nav-item {
    width: 48px;
    min-height: 46px;
    justify-content: center;
    padding: 6px;
  }

  .nav-item__icon {
    width: 34px;
    height: 34px;
  }

  .nav-item__marker {
    right: -7px;
  }

  .nav-footer {
    width: 100%;
  }

  .nav-item--settings {
    width: 48px;
    margin: 0 auto;
  }

  .backend-card {
    width: 36px;
    height: 30px;
    justify-content: center;
    margin: 0 auto;
    padding: 0;
  }
}
</style>
