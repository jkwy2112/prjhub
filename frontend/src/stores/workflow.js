import { defineStore } from 'pinia'
import api from '../api'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    statuses: [],
    usedKeys: [],
    loaded: false,
  }),
  getters: {
    labelOf: (s) => (key) => s.statusMap[key]?.name || key,
    colorOf: (s) => (key) => s.statusMap[key]?.color || '#909399',
    statusMap: (s) => Object.fromEntries(s.statuses.map((x) => [x.key, x])),
    initialKey: (s) => s.statuses.find((x) => x.is_initial)?.key || '',
    doneKeys: (s) => s.statuses.filter((x) => x.is_done).map((x) => x.key),
    isDone: (s) => (key) => s.statusMap[key]?.is_done || false,
    nextKeysOf: (s) => (key) => s.statusMap[key]?.next_keys || [],
  },
  actions: {
    async fetch(force = false) {
      if (this.loaded && !force) return
      const { data } = await api.get('/workflow')
      this.statuses = data.statuses
      this.usedKeys = data.used_keys
      this.loaded = true
    },
  },
})
