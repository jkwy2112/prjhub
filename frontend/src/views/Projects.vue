<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="showArchived">
        <el-radio-button :value="false">进行中</el-radio-button>
        <el-radio-button :value="true">已归档</el-radio-button>
      </el-radio-group>
      <el-button type="primary" :icon="Plus" @click="dialog = true">新建项目</el-button>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="6" v-for="p in projects" :key="p.id" style="margin-bottom: 16px">
        <el-card shadow="hover" class="project-card" @click="$router.push(`/projects/${p.id}`)">
          <div class="project-head">
            <span class="project-key" :style="{ background: p.color }">{{ p.key }}</span>
            <el-tag v-if="p.my_role === 'owner' || p.my_role === 'admin'" size="small" :type="p.my_role === 'owner' ? 'danger' : 'warning'">
              {{ ROLE_META[p.my_role]?.label }}
            </el-tag>
          </div>
          <div class="project-name">{{ p.name }}</div>
          <div class="project-desc">{{ p.description || '暂无描述' }}</div>
          <div class="project-stats">
            <span><el-icon><User /></el-icon> {{ p.member_count }} 成员</span>
            <span><el-icon><Tickets /></el-icon> {{ p.task_count }} 任务</span>
            <span v-if="p.repo_path" class="repo-badge"><el-icon><FolderOpened /></el-icon> Git</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="24" v-if="!loading && !projects.length">
        <el-empty description="还没有项目, 点击右上角新建">
          <el-button type="primary" @click="dialog = true">新建项目</el-button>
        </el-empty>
      </el-col>
    </el-row>

    <el-dialog v-model="dialog" title="新建项目" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="项目标识" required>
          <el-input v-model="form.key" placeholder="大写字母, 如 PRJ (任务编号前缀)" maxlength="16"
            style="width: 200px" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="如: 官网改版" maxlength="64" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" />
        </el-form-item>
        <el-form-item label="Git 仓库">
          <el-switch v-model="form.init_git_repo" active-text="自动初始化空仓库 (git init --bare)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, User, Tickets, FolderOpened } from '@element-plus/icons-vue'
import api from '../api'
import { ROLE_META } from '../constants'

const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const showArchived = ref(false)
const projects = ref([])
const form = reactive({ key: '', name: '', description: '', color: '#409EFF', init_git_repo: true })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/projects', { params: { archived: showArchived.value } })
    projects.value = data
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.key || !form.name) return ElMessage.warning('请填写项目标识和名称')
  saving.value = true
  try {
    await api.post('/projects', form)
    ElMessage.success('项目创建成功' + (form.init_git_repo ? ', Git 仓库已初始化' : ''))
    dialog.value = false
    Object.assign(form, { key: '', name: '', description: '', color: '#409EFF', init_git_repo: true })
    load()
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

onMounted(load)
watch(showArchived, load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
.project-card { cursor: pointer; border-radius: 10px; }
.project-head { display: flex; justify-content: space-between; align-items: center; }
.project-key {
  color: #fff; font-weight: 700; font-size: 12px;
  padding: 3px 8px; border-radius: 6px;
}
.project-name { font-size: 16px; font-weight: 600; margin-top: 10px; color: #303133; }
.project-desc {
  color: #909399; font-size: 12px; margin: 8px 0 12px;
  height: 32px; overflow: hidden; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.project-stats { display: flex; gap: 14px; color: #909399; font-size: 12px; }
.project-stats span { display: flex; align-items: center; gap: 3px; }
.repo-badge { color: #409EFF; }
</style>
