<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

import AppTitleBar from '@/components/AppTitleBar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import SideNav from '@/components/SideNav.vue'
import ToastHost from '@/components/ToastHost.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
let healthTimer = null

onMounted(() => {
  appStore.refreshHealth()
  healthTimer = window.setInterval(() => appStore.refreshHealth(), 30000)
})

onBeforeUnmount(() => {
  if (healthTimer) window.clearInterval(healthTimer)
})
</script>

<template>
  <div class="app-window">
    <div class="ambient ambient--one"></div>
    <div class="ambient ambient--two"></div>
    <div class="ambient-grid"></div>

    <AppTitleBar />

    <div class="app-body">
      <SideNav />
      <main class="content-shell">
        <div class="content-sheen"></div>
        <RouterView v-slot="{ Component, route }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <ToastHost />
    <ConfirmDialog />
  </div>
</template>

<style scoped>
.app-window {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  isolation: isolate;
  background: var(--bg-0);
}

.ambient {
  position: fixed;
  z-index: -2;
  border-radius: 50%;
  pointer-events: none;
}

.ambient--one {
  top: -190px;
  right: -150px;
  width: 430px;
  height: 430px;
  background: #e6f2e7;
}

.ambient--two {
  bottom: -200px;
  left: -140px;
  width: 360px;
  height: 360px;
  background: #f8eee7;
}

.ambient-grid {
  display: none;
}

.app-body {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 12px;
  padding: 0 14px 14px;
}

.content-shell {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--stroke);
  border-radius: var(--radius-xl);
  background: var(--surface-1);
  box-shadow: var(--shadow-sm);
}

.content-sheen {
  display: none;
}

.content-shell :deep(.page) {
  position: relative;
  z-index: 1;
}

@media (max-width: 1120px) {
  .app-body {
    gap: 8px;
    padding-inline: 10px;
    padding-bottom: 10px;
  }
}
</style>
