<script setup>
import { CheckCircle2, CircleAlert, Info, TriangleAlert, X } from '@lucide/vue'

import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const icons = {
  success: CheckCircle2,
  error: CircleAlert,
  warning: TriangleAlert,
  info: Info,
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div
          v-for="item in toast.items"
          :key="item.id"
          class="toast"
          :class="`toast--${item.type}`"
        >
          <span class="toast-icon">
            <component :is="icons[item.type] || Info" :size="17" />
          </span>
          <span class="toast-message">{{ item.message }}</span>
          <button class="toast-close" type="button" @click="toast.dismiss(item.id)">
            <X :size="14" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 62px;
  right: 20px;
  z-index: 1200;
  display: flex;
  width: min(360px, calc(100vw - 32px));
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 11px 11px 13px;
  border: 1px solid var(--stroke);
  border-radius: 13px;
  color: var(--text-1);
  background: var(--surface-1);
  box-shadow: var(--shadow-md);
  pointer-events: auto;
}

.toast-icon {
  display: grid;
  width: 26px;
  height: 26px;
  flex: none;
  place-items: center;
  border-radius: 8px;
  color: var(--accent-deep);
  background: var(--accent-soft);
}

.toast--success .toast-icon {
  color: var(--success);
  background: var(--success-soft);
}

.toast--error .toast-icon {
  color: var(--danger);
  background: var(--danger-soft);
}

.toast--warning .toast-icon {
  color: var(--warning);
  background: var(--warning-soft);
}

.toast-message {
  flex: 1;
  padding-top: 2px;
  font-size: 12.5px;
  line-height: 1.55;
  white-space: pre-line;
}

.toast-close {
  display: grid;
  width: 24px;
  height: 24px;
  flex: none;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
}

.toast-close:hover {
  color: var(--text-1);
  background: var(--surface-3);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 180ms var(--ease-out),
    transform 240ms var(--ease-spring);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(18px) scale(0.98);
}

.toast-move {
  transition: transform 220ms var(--ease-out);
}
</style>
