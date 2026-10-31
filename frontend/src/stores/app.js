import { defineStore } from 'pinia'

import { checkApiHealth, getServiceInfo } from '@/api/http'

export const useAppStore = defineStore('app', {
  state: () => ({
    backendStatus: 'checking',
    serviceInfo: null,
    timetableVersion: 0,
  }),

  getters: {
    backendOnline: (state) => state.backendStatus === 'online',
  },

  actions: {
    async refreshHealth() {
      this.backendStatus = 'checking'
      const online = await checkApiHealth()
      this.backendStatus = online ? 'online' : 'offline'
      if (online && !this.serviceInfo) {
        try {
          this.serviceInfo = await getServiceInfo()
        } catch {
          this.serviceInfo = null
        }
      }
      return online
    },

    markTimetableChanged() {
      this.timetableVersion += 1
    },
  },
})
