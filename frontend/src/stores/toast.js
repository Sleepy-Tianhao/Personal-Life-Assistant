import { defineStore } from 'pinia'

let nextId = 1

export const useToastStore = defineStore('toast', {
  state: () => ({
    items: [],
  }),

  actions: {
    push(message, type = 'info', duration = 3600) {
      if (!message) return
      const id = nextId++
      this.items.push({ id, message, type })
      if (duration > 0) {
        window.setTimeout(() => this.dismiss(id), duration)
      }
    },

    success(message, duration) {
      this.push(message, 'success', duration)
    },

    error(message, duration = 5200) {
      this.push(message, 'error', duration)
    },

    warning(message, duration = 5200) {
      this.push(message, 'warning', duration)
    },

    info(message, duration) {
      this.push(message, 'info', duration)
    },

    dismiss(id) {
      this.items = this.items.filter((item) => item.id !== id)
    },
  },
})
