import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (detail?.[0]?.msg || err.message || '请求失败')
    if (err.response?.status === 401 && location.pathname !== '/login') {
      localStorage.removeItem('token')
      location.href = '/login'
    } else if (typeof detail === 'string') {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export default api
