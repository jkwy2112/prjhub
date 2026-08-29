<template>
  <div class="af-designer" v-if="wf">
    <div class="af-toolbar">
      <div class="af-toolbar-left">
        <el-button :icon="Back" text @click="$router.push('/admin/workflows')">返回</el-button>
        <el-input v-model="wf.name" style="width: 200px" size="small" maxlength="64" />
        <el-input v-model="wf.description" style="width: 280px" size="small" placeholder="描述" maxlength="255" />
      </div>
      <div>
        <el-button size="small" :icon="Plus" @click="appendNode">在末尾添加状态</el-button>
        <el-button size="small" type="primary" :loading="saving" :icon="Check" @click="save">保存</el-button>
      </div>
    </div>

    <div class="af-canvas" v-loading="loading">
      <div class="af-flow">
        <div class="af-terminal">
          <div class="terminal-pill start">流程入口 · {{ initialName }}</div>
        </div>
        <div class="af-link-line"></div>

        <template v-for="(node, idx) in nodes" :key="node.key">
          <div class="af-node-wrap">
            <div class="af-node" :class="{ initial: node.is_initial, done: node.is_done }"
              :style="{ '--node-color': node.color }" @click="openSetting(node)">
              <span class="af-node-del" v-if="!node.is_initial"
                @click.stop="removeNode(node)"><el-icon><Close /></el-icon></span>
              <div class="af-node-head">
                <span class="af-dot"></span>
                <span class="af-node-name">{{ node.name }}</span>
                <span v-if="node.is_initial" class="af-badge">入口</span>
                <span v-if="node.is_done" class="af-badge done">完成态</span>
                <span v-if="(node.next_keys || []).length > 1" class="af-badge branch">分支</span>
              </div>
              <div class="af-node-sub">
                <span>处理: {{ handlerLabel(node) }}</span>
                <span class="af-next">流转: {{ nextNames(node) || '—' }}</span>
              </div>
              <div class="af-node-foot">点击配置</div>
            </div>
          </div>

          <div v-if="idx < nodes.length - 1" class="af-plus" @click="insertAfter(idx)">
            <span class="af-plus-btn"><el-icon><Plus /></el-icon></span>
          </div>
          <div v-else class="af-plus" @click="insertAfter(idx)">
            <span class="af-plus-btn"><el-icon><Plus /></el-icon></span>
          </div>
        </template>

        <div class="af-link-line"></div>
        <div class="af-terminal">
          <div class="terminal-pill end">流程终点 · {{ doneNames }}</div>
        </div>
      </div>
    </div>

    <el-drawer v-model="settingVisible" size="420px" :with-header="true"
      :title="`节点设置 · ${editing?.name || ''}`" append-to-body>
      <el-form v-if="editing" label-width="90px" size="default">
        <el-form-item label="名称">
          <el-input v-model="editing.name" maxlength="32" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="editing.color" />
        </el-form-item>
        <el-form-item label="初始状态">
          <el-switch :model-value="editing.is_initial" @change="setInitial(editing)" />
          <span class="form-tip">新任务创建时进入该状态</span>
        </el-form-item>
        <el-form-item label="完成状态">
          <el-switch v-model="editing.is_done" />
          <span class="form-tip">计入已完成, 不再计入待办</span>
        </el-form-item>
        <el-divider style="margin: 10px 0">流转规则</el-divider>
        <el-form-item label="可流转到">
          <el-select :model-value="editing.next_keys" multiple style="width: 100%"
            @update:model-value="(v) => (editing.next_keys = v)">
            <el-option v-for="o in nodes.filter((x) => x.key !== editing.key)" :key="o.key"
              :value="o.key" :label="o.name" />
          </el-select>
        </el-form-item>
        <el-divider style="margin: 10px 0">处理人规则</el-divider>
        <el-form-item label="谁可流转">
          <el-radio-group v-model="editing.handler_type">
            <el-radio-button value="any">任何人</el-radio-button>
            <el-radio-button value="assignee">负责人</el-radio-button>
            <el-radio-button value="admins">项目管理员</el-radio-button>
            <el-radio-button value="members">指定成员</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="editing.handler_type === 'members'" label="成员">
          <el-select v-model="editing.handler_user_ids" multiple filterable remote
            :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :value="u.id"
              :label="u.name || u.username" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="danger" plain :icon="Delete" v-if="canDelete(editing)"
            @click="removeNode(editing)">删除此节点</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingVisible = false">关闭</el-button>
        <el-button type="primary" @click="settingVisible = false">完成</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Plus, Check, Delete, Close } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const wfId = Number(route.params.id)

const wf = ref(null)
const nodes = ref([])
const loading = ref(false)
const saving = ref(false)
const userOptions = ref([])

const settingVisible = ref(false)
const editing = ref(null)

const HANDLER_LABELS = { any: '任何人', assignee: '负责人', admins: '项目管理员', members: '指定成员' }

function handlerLabel(n) {
  return HANDLER_LABELS[n.handler_type] || '任何人'
}

const initialName = computed(() => nodes.value.find((n) => n.is_initial)?.name || '未设置')
const doneNames = computed(
  () => nodes.value.filter((n) => n.is_done).map((n) => n.name).join(' / ') || '未设置'
)

function nextNames(node) {
  const names = (node.next_keys || [])
    .map((k) => nodes.value.find((x) => x.key === k)?.name)
    .filter(Boolean)
  return names.join('、')
}

function openSetting(node) {
  editing.value = node
  settingVisible.value = true
}

function canDelete(node) {
  return !node.is_initial
}

function setInitial(node) {
  nodes.value.forEach((n) => (n.is_initial = n.key === node.key))
}

function newNode(name) {
  return {
    key: `node_${Date.now().toString(36)}`,
    name: name || `新状态${nodes.value.length + 1}`,
    color: '#9254de',
    x: 0, y: 0,
    is_initial: false,
    is_done: false,
    next_keys: [],
    handler_type: 'any',
    handler_user_ids: [],
  }
}

function insertAfter(idx) {
  const prev = nodes.value[idx]
  const node = newNode()
  // linear-insert semantics: inherit prev's outgoing edges, prev now flows into the new node
  node.next_keys = [...(prev.next_keys || [])]
  prev.next_keys = [node.key]
  nodes.value.splice(idx + 1, 0, node)
  openSetting(node)
}

function appendNode() {
  const last = nodes.value[nodes.value.length - 1]
  const node = newNode()
  if (last && !(last.next_keys || []).length) last.next_keys = [node.key]
  nodes.value.push(node)
  openSetting(node)
}

function removeNode(node) {
  if (node.is_initial) return ElMessage.warning('初始状态不能删除, 请先把其他节点设为初始')
  // rewire: predecessors of the removed node flow to its successors
  const succ = node.next_keys || []
  nodes.value.forEach((n) => {
    if ((n.next_keys || []).includes(node.key)) {
      n.next_keys = [...new Set([...n.next_keys.filter((k) => k !== node.key), ...succ])]
    }
  })
  nodes.value = nodes.value.filter((n) => n.key !== node.key)
  if (editing.value?.key === node.key) settingVisible.value = false
}

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

async function save() {
  if (!wf.value.name.trim()) return ElMessage.warning('请填写工作流名称')
  const initials = nodes.value.filter((n) => n.is_initial)
  if (initials.length !== 1) return ElMessage.warning('必须且只能有一个初始状态')
  saving.value = true
  try {
    const payload = {
      name: wf.value.name,
      description: wf.value.description || '',
      nodes: nodes.value.map((n, i) => ({
        key: n.key, name: n.name, color: n.color,
        x: Math.round(n.x || 0), y: i * 140, // vertical layout keeps y for backward compat
        is_initial: !!n.is_initial, is_done: !!n.is_done,
        next_keys: (n.next_keys || []).filter(
          (k) => k !== n.key && nodes.value.some((x) => x.key === k)
        ),
        handler_type: n.handler_type || 'any',
        handler_user_ids: n.handler_user_ids || [],
      })),
    }
    const { data } = await api.put(`/workflows/${wfId}`, payload)
    if (data.migrated) ElMessage.warning(`已保存, ${data.migrated} 个任务被迁移到初始状态`)
    else ElMessage.success('工作流已保存')
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/workflows/${wfId}`)
    wf.value = { id: data.id, name: data.name, description: data.description }
    nodes.value = data.nodes.map((n) => ({
      ...n, next_keys: [...n.next_keys], handler_user_ids: [...n.handler_user_ids],
    }))
    await Promise.all(
      nodes.value.flatMap((n) => n.handler_user_ids || []).map(async (id) => {
        try {
          const { data } = await api.get('/users', { params: { q: String(id) } })
          const hit = data.find((u) => u.id === id)
          if (hit && !userOptions.value.some((u) => u.id === id)) userOptions.value.push(hit)
        } catch { /* ignore */ }
      })
    )
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.af-designer { display: flex; flex-direction: column; height: calc(100vh - 190px);
  background: #fff; border-radius: 8px; overflow: hidden; }
.af-toolbar { display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-bottom: 1px solid #ebeef5; }
.af-toolbar-left { display: flex; align-items: center; gap: 8px; }
.af-canvas { flex: 1; overflow: auto; background:
  radial-gradient(circle, #eef1f5 1px, transparent 1px) 0 0 / 20px 20px, #f7f8fa; }
.af-flow { width: 480px; margin: 0 auto; padding: 30px 0 60px; }

.af-terminal { display: flex; justify-content: center; }
.terminal-pill { padding: 6px 22px; border-radius: 20px; font-size: 13px; color: #fff; }
.terminal-pill.start { background: #67c23a; }
.terminal-pill.end { background: #909399; }

.af-link-line { width: 2px; height: 26px; background: #cdd4dc; margin: 0 auto; }

.af-node-wrap { display: flex; justify-content: center; }
.af-node {
  position: relative; width: 100%; background: #fff; border-radius: 10px;
  border: 1.5px solid var(--node-color, #dcdfe6); cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: box-shadow 0.15s, transform 0.15s;
}
.af-node:hover { box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12); transform: translateY(-1px); }
.af-node-head { display: flex; align-items: center; gap: 8px; padding: 12px 14px 4px; }
.af-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--node-color); }
.af-node-name { font-size: 15px; font-weight: 600; color: #303133; }
.af-badge {
  font-size: 11px; padding: 1px 8px; border-radius: 10px;
  background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8;
}
.af-badge.done { background: #ecf5ff; color: #409eff; border-color: #d9ecff; }
.af-badge.branch { background: #fdf6ec; color: #e6a23c; border-color: #faecd8; }
.af-node-sub { padding: 4px 14px 8px; display: flex; flex-direction: column; gap: 2px;
  font-size: 12px; color: #909399; }
.af-next { color: #606266; }
.af-node-foot {
  border-top: 1px dashed #ebeef5; text-align: center; font-size: 11px;
  color: #c0c4cc; padding: 4px 0;
}
.af-node-del {
  position: absolute; top: -9px; right: -9px; width: 20px; height: 20px;
  border-radius: 50%; background: #f56c6c; color: #fff; cursor: pointer;
  display: none; align-items: center; justify-content: center; font-size: 12px;
}
.af-node:hover .af-node-del { display: flex; }

.af-plus { display: flex; justify-content: center; height: 30px; align-items: center; }
.af-plus-btn {
  width: 26px; height: 26px; border-radius: 50%; background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.4); transition: transform 0.15s;
}
.af-plus-btn:hover { transform: scale(1.15); }
.form-tip { font-size: 12px; color: #c0c4cc; margin-left: 8px; }
</style>
