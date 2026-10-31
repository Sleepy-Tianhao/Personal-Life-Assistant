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
}

.ambient {
  position: fixed;
  z-index: -2;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  opacity: 0.52;
}

.ambient--one {
  top: -28vh;
  right: 8vw;
  width: 54vw;
  height: 62vh;
  background: radial-gradient(circle, rgba(40, 112, 255, 0.52), transparent 68%);
}

.ambient--two {
  bottom: -34vh;
  left: -12vw;
  width: 48vw;
  height: 58vh;
  background: radial-gradient(circle, rgba(16, 117, 169, 0.34), transparent 68%);
}

.ambient-grid {
  position: fixed;
  inset: 0;
  z-index: -1;
  opacity: 0.2;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: radial-gradient(ellipse 80% 64% at 52% 22%, black 20%, transparent 78%);
  pointer-events: none;
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
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.035), transparent 42%),
    rgba(9, 13, 20, 0.66);
  box-shadow:
    0 28px 80px rgba(0, 0, 0, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(22px) saturate(1.2);
}

.content-sheen {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background:
    radial-gradient(900px 460px at 28% -12%, rgba(59, 135, 255, 0.12), transparent 58%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.018), transparent 18%);
  pointer-events: none;
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
