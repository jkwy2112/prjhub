export const STATUS_META = {
  todo: { label: '待办', color: '#909399' },
  in_progress: { label: '进行中', color: '#409EFF' },
  testing: { label: '测试中', color: '#E6A23C' },
  done: { label: '已完成', color: '#67C23A' },
}

export const STATUS_ORDER = ['todo', 'in_progress', 'testing', 'done']

export const TYPE_META = {
  requirement: { label: '需求', color: '#409EFF', icon: 'Collection' },
  task: { label: '任务', color: '#67C23A', icon: 'Tickets' },
  bug: { label: '缺陷', color: '#F56C6C', icon: 'WarningFilled' },
}

export const PRIORITY_META = {
  low: { label: '低', type: 'info' },
  medium: { label: '中', type: 'primary' },
  high: { label: '高', type: 'warning' },
  urgent: { label: '紧急', type: 'danger' },
}

export const ROLE_META = {
  owner: { label: '所有者', type: 'danger' },
  admin: { label: '管理员', type: 'warning' },
  member: { label: '成员', type: 'info' },
}

export function fmtDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function fmtDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
