// Verify FormControlConfig actually renders per-control property panels
import { createServer } from 'vite'
import path from 'node:path'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ElementPlus, { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const root = process.cwd()
const server = await createServer({ root, logLevel: 'error', server: { middlewareMode: true }, appType: 'custom' })
server.config.resolve.dedupe = ['vue', 'vue-router', 'pinia', 'element-plus']

globalThis.window = globalThis
globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} }
globalThis.location = { origin: 'http://l', pathname: '/', href: '' }
globalThis.document = { currentScript: { src: '' }, querySelector: () => null, querySelectorAll: () => [],
  createElement: () => ({ style: {}, setAttribute: () => {}, appendChild: () => {} }), createTextNode: () => ({}),
  addEventListener: () => {}, documentElement: { style: {} }, body: { appendChild: () => {}, style: {} } }

const apiMod = await server.ssrLoadModule(path.join(root, 'src/api/index.js'))
const api = apiMod.default
api.get = () => Promise.resolve({ data: [] })
api.post = () => Promise.resolve({ data: {} })

const { newFormItem } = await server.ssrLoadModule(path.join(root, 'src/components/form/formComponents.js'))
const mod = await server.ssrLoadModule(path.join(root, 'src/components/form/FormControlConfig.vue'))
const Config = mod.default

const CASES = ['AmountInput', 'DateTime', 'SelectInput', 'ImageUpload', 'FileUpload', 'TableList', 'UserPicker', 'TextInput']
let fail = 0
for (const name of CASES) {
  const item = newFormItem(name)
  const app = createSSRApp({ render: () => h(Config, { item }) })
  app.use(ElementPlus, { locale: zhCn })
  app.provide(ID_INJECTION_KEY, { prefix: 1024, current: 0 })
  app.provide(ZINDEX_INJECTION_KEY, { initialZIndex: 2000, currentZIndex: 0, nextZIndex: () => 2001 })
  try {
    const html = await renderToString(app)
    const expect = {
      AmountInput: ['保留小数', '展示大写'],
      DateTime: ['日期格式'],
      SelectInput: ['选项设置', '选项展开'],
      ImageUpload: ['数量限制', '大小限制'],
      FileUpload: ['文件类型'],
      TableList: ['明细列', '汇总行'],
      UserPicker: ['多选'],
      TextInput: ['提示文字'],
    }[name] || []
    const missing = expect.filter((k) => !html.includes(k))
    if (missing.length) { console.log(`FAIL ${name}: missing ${missing.join(',')}`); fail++ }
    else console.log(`OK   ${name} 属性面板渲染正确 (${html.length} chars)`)
  } catch (e) {
    console.log(`FAIL ${name}: ${e.message}`); fail++
  }
}
console.log(fail ? `${fail} FAILED` : 'ALL CONTROL CONFIG PANELS OK')
await server.close()
process.exit(fail ? 1 : 0)
