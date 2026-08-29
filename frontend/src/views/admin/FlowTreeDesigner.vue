<template>
  <div class="wf-designer">
    <div class="wf-toolbar">
      <div class="wf-toolbar-left">
        <el-button :icon="Back" text @click="$router.push('/admin/flows')">返回</el-button>
        <el-input v-model="defName" style="width: 220px" size="small" placeholder="流程名称" maxlength="64" />
        <el-input v-model="defKey" style="width: 200px" size="small" placeholder="标识(小写字母)" maxlength="64"
          :disabled="!!definitionId" />
      </div>
      <div>
        <el-button size="small" @click="resetTree">清空重画</el-button>
        <el-button size="small" type="primary" :loading="saving" :icon="Check" @click="save">保存并发布</el-button>
      </div>
    </div>

    <div class="wf-body">
      <div class="wf-canvas">
        <div class="wf-root-row">
          <div class="wf-start-pill">发起人 · 所有人</div>
          <div class="wf-link"></div>
        </div>
        <WfNode :node="tree" :selected="selected" @select="selected = $event" @self-remove="tree.childNode = null" />
        <template v-if="!tree.childNode">
          <div class="wf-plus-row">
            <el-popover placement="bottom-start" trigger="click" width="290">
              <template #reference>
                <span class="wf-plus-btn"><el-icon><Plus /></el-icon></span>
              </template>
              <div class="wf-menu">
                <div class="wf-menu-item" @click="addFirst('APPROVAL')">
                  <el-icon style="color: #ff943e"><User /></el-icon>审批人
                </div>
                <div class="wf-menu-item" @click="addFirst('CONDITIONS')">
                  <el-icon style="color: #15bc83"><Share /></el-icon>条件分支
                </div>
                <div class="wf-menu-item" @click="addFirst('CONCURRENTS')">
                  <el-icon style="color: #718dff"><Operation /></el-icon>并行分支
                </div>
              </div>
            </el-popover>
          </div>
          <p class="wf-empty-tip">从上方「+」开始搭建流程</p>
        </template>
        <div v-if="tree.childNode" class="wf-link"></div>
        <div v-if="tree.childNode" class="wf-end-pill">流程结束 (通过 / 驳回)</div>
      </div>

      <div class="wf-props">
        <el-empty v-if="!selected" description="点击节点配置属性" :image-size="70" />
        <template v-else>
          <h4>{{ typeLabel }}</h4>

          <!-- approval -->
          <template v-if="selected.type === 'APPROVAL'">
            <el-form label-width="90px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-form-item label="审批人">
                <el-radio-group v-model="selected.props.assigneeType">
                  <el-radio-button value="users">固定成员</el-radio-button>
                  <el-radio-button value="runtime">发起时指定</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selected.props.assigneeType === 'users'" label="成员">
                <el-select v-model="selected.props.users" multiple filterable remote
                  :remote-method="searchUsers" placeholder="搜索用户" style="width: 100%">
                  <el-option v-for="u in userOptions" :key="u.id" :value="u.id"
                    :label="u.name || u.username" />
                </el-select>
              </el-form-item>
              <el-form-item v-else label="说明">
                <span class="tip">发起审批时由发起人选择审批人</span>
              </el-form-item>
              <el-form-item label="签核模式">
                <el-radio-group v-model="selected.props.mode">
                  <el-radio-button value="any">或签</el-radio-button>
                  <el-radio-button value="all">会签</el-radio-button>
                  <el-radio-button value="count">票签</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selected.props.mode === 'count'" label="通过票数">
                <el-input-number v-model="selected.props.count" :min="1" />
              </el-form-item>
            </el-form>
          </template>

          <!-- condition branch -->
          <template v-else-if="selected.type === 'CONDITION'">
            <el-form label-width="90px" size="small">
              <el-form-item label="分支名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <el-divider style="margin: 8px 0">满足以下条件</el-divider>
              <div v-for="(group, gi) in groupsWithCond" :key="gi" class="cond-group">
                <div class="cond-group-head">
                  <el-radio-group v-model="selected.props.groupsType" size="small" v-if="groupsWithCond.length > 1">
                    <el-radio-button value="AND">条件组 且</el-radio-button>
                    <el-radio-button value="OR">条件组 或</el-radio-button>
                  </el-radio-group>
                  <span v-else class="tip">条件组</span>
                  <el-button text type="danger" size="small" v-if="groupsWithCond.length > 1"
                    @click="selected.props.groups.splice(gi, 1)">删除组</el-button>
                </div>
                <div v-for="(cond, ci) in group.conditions" :key="ci" class="cond-row">
                  <el-input v-model="cond.field" placeholder="字段" style="width: 90px" size="small" />
                  <el-select v-model="cond.compare" size="small" style="width: 86px">
                    <el-option value=">" label=">" /><el-option value=">=" label=">=" />
                    <el-option value="<" label="<" /><el-option value="<=" label="<=" />
                    <el-option value="==" label="=" />
                    <el-option value="between" label="区间" />
                    <el-option value="in" label="属于" />
                  </el-select>
                  <template v-if="cond.compare === 'between'">
                    <el-input v-model="cond.value[0]" placeholder="下限" style="width: 70px" size="small" />
                    <el-input v-model="cond.value[1]" placeholder="上限" style="width: 70px" size="small" />
                  </template>
                  <el-input v-else v-model="cond.value[0]" placeholder="值" style="width: 80px" size="small" />
                  <el-button text type="danger" size="small" @click="group.conditions.splice(ci, 1)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
                <div class="cond-ops">
                  <el-button v-if="group.conditions.length > 1" text size="small"
                    @click="group.groupType = group.groupType === 'AND' ? 'OR' : 'AND'">
                    组内: {{ group.groupType === 'AND' ? '且' : '或' }}
                  </el-button>
                  <el-button text size="small" :icon="Plus"
                    @click="group.conditions.push({ field: 'amount', compare: '>', value: [0] })">加条件</el-button>
                </div>
              </div>
              <el-button text size="small" :icon="Plus"
                @click="selected.props.groups.push({ groupType: 'AND', conditions: [] })">加条件组</el-button>
              <el-alert v-if="!hasAnyCondition" type="warning" :closable="false" style="margin-top: 8px"
                title="无条件 = 默认分支 (前面条件都不满足时走此分支)" />
            </el-form>
          </template>

          <!-- branch (parallel) -->
          <template v-else-if="selected.type === 'BRANCH'">
            <el-form label-width="90px" size="small">
              <el-form-item label="分支名称">
                <el-input v-model="selected.name" maxlength="32" />
              </el-form-item>
              <p class="tip">并行分支内的节点同时执行, 全部完成后汇聚继续</p>
            </el-form>
          </template>

          <!-- group node itself -->
          <template v-else-if="selected.type === 'CONDITIONS' || selected.type === 'CONCURRENTS'">
            <p class="tip">
              {{ selected.type === 'CONDITIONS'
                ? '自上而下按优先级匹配, 命中一个分支即走 (无条件分支为默认兜底)'
                : '所有分支同时执行, 全部完成后汇聚到后续节点' }}
            </p>
          </template>
          <template v-else>
            <p class="tip">根节点无需配置</p>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Plus, Check, Close, User, Share, Operation } from '@element-plus/icons-vue'
import api from '../../api'
import WfNode from '../../components/flow/WfNode.vue'

const route = useRoute()
const definitionId = route.params.id ? Number(route.params.id) : null

const defKey = ref('')
const defName = ref('')
const tree = reactive({ type: 'ROOT', name: '发起人', childNode: null })
const selected = ref(null)
const saving = ref(false)
const userOptions = ref([])

const typeLabel = computed(() => ({
  APPROVAL: '审批节点', CONDITION: '条件分支', BRANCH: '并行分支',
  CONDITIONS: '条件分支组', CONCURRENTS: '并行分支组', ROOT: '发起人',
}[selected.value?.type] || ''))

const groupsWithCond = computed(() => selected.value?.props?.groups || [])
const hasAnyCondition = computed(
  () => !(selected.value?.props?.groups || []).some((g) => (g.conditions || []).length))

async function searchUsers(q) {
  if (!q) return (userOptions.value = [])
  const { data } = await api.get('/users', { params: { q } })
  userOptions.value = data
}

function newNode(type) {
  if (type === 'APPROVAL') {
    return { type, name: '审批节点', props: { assigneeType: 'users', users: [], mode: 'any', count: 2 }, childNode: null }
  }
  if (type === 'CONDITIONS') {
    return {
      type, name: '条件分支', childNode: null,
      branches: [
        { type: 'CONDITION', name: '条件1', childNode: null,
          props: { groupsType: 'AND', groups: [{ groupType: 'AND', conditions: [] }] } },
        { type: 'CONDITION', name: '默认', childNode: null, props: { groupsType: 'AND', groups: [] } },
      ],
    }
  }
  return {
    type: 'CONCURRENTS', name: '并行分支', childNode: null,
    branches: [
      { type: 'BRANCH', name: '分支1', childNode: null },
      { type: 'BRANCH', name: '分支2', childNode: null },
    ],
  }
}

function addFirst(type) {
  const node = newNode(type)
  node.childNode = tree.childNode
  tree.childNode = node
  selected.value = node
}

function resetTree() {
  tree.childNode = null
  selected.value = null
}

async function loadUsersByIds(ids) {
  await Promise.all([...new Set(ids)].map(async (id) => {
    try {
      const { data } = await api.get('/users', { params: { q: String(id) } })
      const hit = data.find((u) => u.id === id)
      if (hit && !userOptions.value.some((u) => u.id === id)) userOptions.value.push(hit)
    } catch { /* ignore */ }
  }))
}

function collectUserIds(node, acc) {
  if (!node) return acc
  if (node.type === 'APPROVAL') acc.push(...(node.props?.users || []))
  ;(node.branches || []).forEach((b) => collectUserIds(b.childNode, acc))
  collectUserIds(node.childNode, acc)
  return acc
}

function collectErrors(node, errs) {
  if (!node) return
  if (node.type === 'APPROVAL') {
    if (node.props?.assigneeType === 'users' && !(node.props.users || []).length) {
      errs.push(`「${node.name}」未指定审批成员`)
    }
  }
  ;(node.branches || []).forEach((b) => {
    if (b.type === 'CONDITION') {
      const hasCond = (b.props?.groups || []).some((g) => (g.conditions || []).length)
      const validConds = (b.props?.groups || []).every((g) =>
        (g.conditions || []).every((c) => c.field && c.value?.length && c.value[0] !== ''))
      if (!hasCond) errs.push(`条件分支「${b.name}」未设置条件 (无条件=默认分支)`)
      else if (!validConds) errs.push(`条件分支「${b.name}」存在未填写完整的条件`)
    }
    collectErrors(b.childNode, errs)
  })
  collectErrors(node.childNode, errs)
}

async function save() {
  if (!defKey.value.trim() || !defName.value.trim()) {
    return ElMessage.warning('请填写流程标识和名称')
  }
  if (!tree.childNode) return ElMessage.warning('流程至少需要一个节点')
  const errs = []
  collectErrors(tree.childNode, errs)
  if (errs.length) {
    ElMessage.warning({ message: errs.slice(0, 3).join('; ') + (errs.length > 3 ? ' …' : ''), duration: 5000 })
    return
  }
  saving.value = true
  try {
    await api.post('/approvals/definitions/tree', {
      key: defKey.value.trim(), name: defName.value.trim(), tree,
    })
    ElMessage.success('流程已发布 (新版本立即生效, 在途单按旧版跑完)')
  } catch { /* interceptor shows compile error */ } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (definitionId) {
    const { data } = await api.get(`/approvals/definitions/${definitionId}/tree`)
    defKey.value = data.key
    defName.value = data.name
    Object.assign(tree, data.tree || { type: 'ROOT', childNode: null })
    await loadUsersByIds(collectUserIds(tree.childNode, []))
  }
})
</script>

<style scoped>
.wf-designer { display: flex; flex-direction: column; height: calc(100vh - 190px);
  background: #fff; border-radius: 8px; overflow: hidden; }
.wf-toolbar { display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-bottom: 1px solid #ebeef5; }
.wf-toolbar-left { display: flex; align-items: center; gap: 8px; }
.wf-body { flex: 1; display: flex; min-height: 0; }
.wf-canvas { flex: 1; overflow: auto; padding: 24px 40px 60px;
  background: radial-gradient(circle, #eef1f5 1px, transparent 1px) 0 0 / 20px 20px, #f7f8fa; }
.wf-root-row { display: flex; flex-direction: column; align-items: center; }
.wf-start-pill, .wf-end-pill { padding: 6px 22px; border-radius: 18px; font-size: 13px; color: #fff; }
.wf-start-pill { background: #409eff; }
.wf-end-pill { background: #909399; }
.wf-link { width: 2px; height: 22px; background: #cacaca; margin: 0 auto; }
.wf-plus-row { display: flex; justify-content: center; padding: 6px 0; }
.wf-plus-btn { width: 28px; height: 28px; border-radius: 50%; background: #409eff; color: #fff;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 6px rgba(64,158,255,.4); }
.wf-empty-tip { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 10px; }
.wf-menu { display: flex; flex-wrap: wrap; gap: 8px; }
.wf-menu-item { display: flex; align-items: center; gap: 6px; width: 115px; padding: 9px 10px;
  cursor: pointer; background: #f8f9f9; border-radius: 8px; font-size: 13px; color: #606266; }
.wf-menu-item:hover { background: #fff; box-shadow: 0 0 8px 2px #d6d6d6; }
.wf-props { width: 360px; border-left: 1px solid #ebeef5; padding: 14px; overflow: auto; }
.wf-props h4 { margin-bottom: 14px; color: #303133; }
.tip { color: #909399; font-size: 12px; }
.cond-group { border: 1px solid #ebeef5; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
.cond-group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.cond-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.cond-ops { display: flex; gap: 8px; margin-top: 4px; }
</style>
