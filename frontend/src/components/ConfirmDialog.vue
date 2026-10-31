<script setup>
import { TriangleAlert } from '@lucide/vue'

import Modal from '@/components/Modal.vue'
import { useDialogStore } from '@/stores/dialog'

const dialog = useDialogStore()
</script>

<template>
  <Modal
    :model-value="dialog.open"
    :title="dialog.title"
    :width="430"
    @update:model-value="(value) => !value && dialog.resolve(false)"
  >
    <div class="confirm-content">
      <span class="confirm-icon" :class="{ 'confirm-icon--danger': dialog.danger }">
        <TriangleAlert :size="21" />
      </span>
      <p>{{ dialog.message }}</p>
    </div>

    <template #footer>
      <button class="btn" type="button" @click="dialog.resolve(false)">
        {{ dialog.cancelText }}
      </button>
      <button
        class="btn"
        :class="dialog.danger ? 'btn-danger' : 'btn-primary'"
        type="button"
        @click="dialog.resolve(true)"
      >
        {{ dialog.confirmText }}
      </button>
    </template>
  </Modal>
</template>

<style scoped>
.confirm-content {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 2px 0 4px;
}

.confirm-icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: none;
  place-items: center;
  border: 1px solid var(--stroke);
  border-radius: 12px;
  color: var(--warning);
  background: var(--warning-soft);
}

.confirm-icon--danger {
  color: var(--danger);
  background: var(--danger-soft);
}

.confirm-content p {
  padding-top: 2px;
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-line;
}
</style>
