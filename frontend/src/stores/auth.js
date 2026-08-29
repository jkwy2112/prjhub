import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    authOptions: { ldap_enabled: false, wecom_enabled: false },
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    displayName: (s) => s.user?.name || s.user?.username || '',
  },
  actions: {
    async fetchOptions() {
      try {
        const { data } = await api.get('/meta/auth-options')
        this.authOptions = data
      } catch { /* ignore */ }
    },
    async login(username, password) {
      const { data } = await api.post('/auth/login', { username, password })
      this.setSession(data)
    },
    async wecomLogin(code) {
      const { data } = await api.post('/auth/wecom', { code })
      this.setSession(data)
    },
    async wecomUrl(redirectUri) {
      const { data } = await api.get('/auth/wecom/url', { params: { redirect_uri: redirectUri } })
      return data.url
    },
    setSession(data) {
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
