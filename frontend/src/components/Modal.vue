<script setup>
import { X } from '@lucide/vue'
import { onBeforeUnmount, onMounted, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: [String, Number], default: 560 },
  closeOnOverlay: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

function onOverlayClick(event) {
  if (props.closeOnOverlay && event.target === event.currentTarget) close()
}

function onKeydown(event) {
  if (event.key === 'Escape' && props.modelValue) close()
}

watch(
  () => props.modelValue,
  (open) => {
    document.documentElement.classList.toggle('modal-open', open)
  },
)

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.documentElement.classList.remove('modal-open')
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-layer" @mousedown="onOverlayClick">
        <section
          class="modal-panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          :style="{ '--modal-width': typeof width === 'number' ? `${width}px` : width }"
        >
          <header class="modal-header">
            <div class="modal-heading">
              <slot name="eyebrow" />
              <h2 v-if="title">{{ title }}</h2>
              <p v-if="subtitle">{{ subtitle }}</p>
            </div>
            <button class="icon-btn" type="button" title="关闭" @click="close">
              <X :size="17" />
            </button>
          </header>

          <div class="modal-body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-layer {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px;
  background: rgba(32, 52, 42, 0.28);
}

.modal-panel {
  display: flex;
  width: min(var(--modal-width, 560px), 100%);
  max-height: min(840px, calc(100vh - 72px));
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--stroke);
  border-radius: 22px;
  background: var(--surface-1);
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 22px 0;
}

.modal-heading {
  min-width: 0;
}

.modal-heading h2 {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 650;
  letter-spacing: -0.03em;
}

.modal-heading p {
  margin-top: 5px;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.55;
}

.modal-body {
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px 22px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 22px 18px;
  border-top: 1px solid var(--stroke);
  background: var(--surface-2);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 180ms var(--ease-out);
}

.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition:
    transform 240ms var(--ease-spring),
    opacity 180ms var(--ease-out);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  opacity: 0;
  transform: translateY(14px) scale(0.97);
}

@media (max-width: 640px) {
  .modal-layer {
    align-items: flex-end;
    padding: 0;
  }

  .modal-panel {
    width: 100%;
    max-height: 92vh;
    border-radius: 22px 22px 0 0;
  }
}
</style>
