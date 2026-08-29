import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'projects', name: 'projects', component: () => import('../views/Projects.vue') },
      { path: 'projects/:id', name: 'project-detail', component: () => import('../views/ProjectDetail.vue') },
      { path: 'my-tasks', name: 'my-tasks', component: () => import('../views/MyTasks.vue') },
      {
        path: 'admin',
        component: () => import('../views/admin/AdminLayout.vue'),
        meta: { requiresSuperuser: true },
        children: [
          { path: '', redirect: '/admin/overview' },
          { path: 'overview', name: 'admin-overview', component: () => import('../views/admin/Overview.vue') },
          { path: 'users', name: 'admin-users', component: () => import('../views/admin/Users.vue') },
          { path: 'workflows', name: 'admin-workflows', component: () => import('../views/admin/WorkflowList.vue') },
          { path: 'workflows/:id', name: 'admin-workflow-designer', component: () => import('../views/admin/WorkflowDesigner.vue') },
          { path: 'auth/ldap', name: 'admin-ldap', component: () => import('../views/admin/LdapConfig.vue') },
          { path: 'im/wecom', name: 'admin-wecom', component: () => import('../views/admin/ImConfig.vue') },
        ],
      },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && token) return { name: 'dashboard' }
  if (to.matched.some((r) => r.meta.requiresSuperuser)) {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (!user?.is_superuser) return { name: 'dashboard' }
  }
  return true
})

export default router
