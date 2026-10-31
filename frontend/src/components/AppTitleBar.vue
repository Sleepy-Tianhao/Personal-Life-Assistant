<script setup>
import { Minus, Square, X } from '@lucide/vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'

import brandMark from '@/assets/brand-mark.svg'
import NowIsland from '@/components/NowIsland.vue'

const desktop = window.desktop || null
const isMaximized = ref(false)
let unsubscribe = null

async function toggleMaximize() {
  if (!desktop) return
  isMaximized.value = await desktop.toggleMaximize()
}

onMounted(async () => {
  if (!desktop) return
  isMaximized.value = await desktop.isMaximized()
  unsubscribe = desktop.onMaximizedChange((value) => {
    isMaximized.value = value
  })
})

onBeforeUnmount(() => {
  unsubscribe?.()
})
</script>

<template>
  <header class="titlebar app-drag">
    <div class="titlebar-brand">
      <img :src="brandMark" alt="" class="brand-mark" />
      <div class="brand-copy">
        <span class="brand-name">Life Assistant</span>
        <span class="brand-caption">PERSONAL DESKTOP</span>
      </div>
    </div>

    <div class="titlebar-center">
      <NowIsland />
    </div>

    <div v-if="desktop" class="window-controls">
      <button class="window-control" title="最小化" @click="desktop.minimize()">
        <Minus :size="15" :stroke-width="1.6" />
      </button>
      <button
        class="window-control"
        :title="isMaximized ? '还原' : '最大化'"
        @click="toggleMaximize"
      >
        <span v-if="isMaximized" class="restore-icon"></span>
        <Square v-else :size="12" :stroke-width="1.5" />
      </button>
      <button
        class="window-control window-control--close"
        title="关闭"
        @click="desktop.close()"
      >
        <X :size="15" :stroke-width="1.6" />
      </button>
    </div>
    <div v-else class="preview-chip">浏览器预览</div>
  </header>
</template>

<style scoped>
.titlebar {
  position: relative;
  z-index: 20;
  display: grid;
  grid-template-columns: minmax(200px, 1fr) auto minmax(200px, 1fr);
  align-items: center;
  height: var(--titlebar-height);
  padding: 0 8px 0 18px;
  box-sizing: border-box;
  user-select: none;
}

.titlebar-brand {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  width: 24px;
  height: 24px;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.08;
}

.brand-name {
  color: var(--text-1);
  font-family: var(--font-display);
  font-size: 12.5px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.brand-caption {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 7.5px;
  font-weight: 680;
  letter-spacing: 0.16em;
}

.titlebar-center {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 18px;
}

.window-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

.window-control {
  display: grid;
  width: 42px;
  height: 32px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  transition:
    color 140ms ease,
    background 140ms ease;
}

.window-control:hover {
  color: var(--text-1);
  background: var(--surface-3);
}

.window-control--close:hover {
  color: #ffffff;
  background: var(--danger);
}

.restore-icon {
  position: relative;
  display: block;
  width: 9px;
  height: 9px;
  border: 1px solid currentColor;
  border-radius: 1px;
}

.restore-icon::before {
  position: absolute;
  top: -3px;
  left: 2px;
  width: 9px;
  height: 9px;
  border: 1px solid currentColor;
  border-radius: 1px;
  background: transparent;
  content: "";
}

.preview-chip {
  justify-self: end;
  padding: 4px 9px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  color: var(--text-3);
  font-size: 10px;
  letter-spacing: 0.02em;
}

@media (max-width: 900px) {
  .titlebar {
    grid-template-columns: auto 1fr auto;
  }

  .brand-copy {
    display: none;
  }

  .titlebar-center {
    padding: 0 10px;
  }
}
</style>
