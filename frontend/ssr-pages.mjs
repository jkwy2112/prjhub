// SSR-render EVERY routed page with mocked api — catches runtime errors before the browser does
import { createServer } from 'vite'
import path from 'node:path'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import ElementPlus, { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const root = process.cwd()
const server = await createServer({ root, logLevel: 'error', server: { middlewareMode: true }, appType: 'custom' })
server.config.resolve.dedupe = ['vue', 'vue-router', 'pinia', 'element-plus']

globalThis.window = globalThis
globalThis.localStorage = { getItem: (k) => (k === 'token' ? 'x' : k === 'user' ? JSON.stringify({ id: 1, is_superuser: true, name: 'a', username: 'a' }) : null), setItem: () => {}, removeItem: () => {} }
globalThis.location = { origin: 'http://l', pathname: '/', href: '' }
globalThis.document = { currentScript: { src: '' }, querySelector: () => null, querySelectorAll: () => [],
  createElement: () => ({ style: {}, setAttribute: () => {}, appendChild: () => {} }), createTextNode: () => ({}),
  addEventListener: () => {}, documentElement: { style: {} }, body: { appendChild: () => {}, style: {} } }
globalThis.ECharts = undefined

const FAKE_GET = {
  '/meta/auth-options': { ldap_enabled: false, wecom_enabled: false },
  '/dashboard': { project_count: 1, my_open_task_count: 0, overdue_task_count: 0, done_task_count: 0, status_distribution: {}, type_distribution: {}, my_recent_tasks: [], recent_activities: [] },
  '/projects': [], '/approvals/my-pending': [], '/approvals/my-submitted': [], '/approvals/definitions': [],
  '/admin/stats': { user_count: 1, active_user_count: 1, project_count: 1, archived_project_count: 0, task_count: 0, task_status_distribution: {}, repo_count: 0, auth_options: {}, recent_users: [] },
  '/admin/users': [], '/admin/auth-config': { ldap: {}, wecom: {} },
  '/users': [], '/approvals/definitions/1/tree': { id: 1, tree: { type: 'ROOT', childNode: null }, form_items: [] },
  '/workflows/default': { nodes: [] }, '/my/tasks': [], '/projects/1': { id: 1, key: 'P', name: 'P', my_role: 'owner' },
  '/projects/1/tasks': [], '/projects/1/members': [], '/projects/1/activities': [], '/projects/1/workflow': { nodes: [] },
  '/approvals/1': { id: 1, tasks: [], form_items: [], form_values: {}, my_pending_task_id: null, status: 'running' },
}
const apiMod = await server.ssrLoadModule(path.join(root, 'src/api/index.js'))
const api = apiMod.default
api.get = (url) => {
  for (const [k, v] of Object.entries(FAKE_GET)) if (url.split('?')[0].startsWith(k)) return Promise.resolve({ data: v })
  return Promise.resolve({ data: [] })
}
api.post = () => Promise.resolve({ data: {} })
api.put = () => Promise.resolve({ data: {} })

const load = (p) => server.ssrLoadModule(path.join(root, p))

const PAGES = [
  ['/dashboard', 'src/views/Dashboard.vue'],
  ['/projects', 'src/views/Projects.vue'],
  ['/my-tasks', 'src/views/MyTasks.vue'],
  ['/approvals', 'src/views/Approvals.vue'],
  ['/admin/overview', 'src/views/admin/Overview.vue'],
  ['/admin/users', 'src/views/admin/Users.vue'],
  ['/admin/flows', 'src/views/admin/FlowTreeList.vue'],
  ['/admin/flows/1', 'src/views/admin/FlowTreeDesigner.vue'],
  ['/admin/auth/ldap', 'src/views/admin/LdapConfig.vue'],
  ['/admin/im/wecom', 'src/views/admin/ImConfig.vue'],
  ['/projects/1', 'src/views/ProjectDetail.vue'],
]

let failed = 0
for (const [routePath, file] of PAGES) {
  try {
    const Comp = (await load(file)).default
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: '/:pathMatch(.*)*', component: Comp }] })
    await router.push(routePath)
    await router.isReady()
    const app = createSSRApp({ render: () => h(Comp) })
    app.use(router); app.use(createPinia())
    app.use(ElementPlus, { locale: zhCn })
    app.provide(ID_INJECTION_KEY, { prefix: 1024, current: 0 })
    app.provide(ZINDEX_INJECTION_KEY, { initialZIndex: 2000, currentZIndex: 0, nextZIndex: () => 2001 })
    const html = await renderToString(app)
    console.log(`OK   ${routePath.padEnd(18)} (${html.length} chars)`)
  } catch (e) {
    failed++
    console.log(`FAIL ${routePath.padEnd(18)} :: ${e.message}`)
    const stackLine = (e.stack || '').split('\n')[1] || ''
    console.log('     ', stackLine.trim())
  }
}
console.log(failed ? `\n${failed} page(s) FAILED` : '\nALL PAGES RENDER OK')
await server.close()
process.exit(failed ? 1 : 0)
