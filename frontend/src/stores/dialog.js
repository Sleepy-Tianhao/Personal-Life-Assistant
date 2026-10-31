import { defineStore } from 'pinia'

let pendingResolve = null

export const useDialogStore = defineStore('dialog', {
  state: () => ({
    open: false,
    title: '',
    message: '',
    confirmText: '确认',
    cancelText: '取消',
    danger: false,
  }),

  actions: {
    ask({
      title = '确认操作',
      message = '',
      confirmText = '确认',
      cancelText = '取消',
      danger = false,
    } = {}) {
      this.open = true
      this.title = title
      this.message = message
      this.confirmText = confirmText
      this.cancelText = cancelText
      this.danger = danger
      return new Promise((resolve) => {
        pendingResolve = resolve
      })
    },

    resolve(value) {
      this.open = false
      const resolver = pendingResolve
      pendingResolve = null
      resolver?.(value)
    },
  },
})
