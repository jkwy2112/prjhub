import { defineStore } from 'pinia'
import api from '../api'

/**
 * Default workflow (system-wide). Used by dashboard/my-tasks rendering.
 * Project pages use their own bound workflow (fetched per project).
 */
export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    statuses: [],
    loaded: false,
  }),
  getters: {
    labelOf: (s) => (key) => s.statusMap[key]?.name || (key === 'other' ? '其他' : key),
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
      const { data } = await api.get('/workflows/default')
      this.statuses = data.nodes
      this.loaded = true
    },
  },
})
