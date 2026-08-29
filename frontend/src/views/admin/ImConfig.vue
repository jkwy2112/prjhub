<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="企业微信" name="wecom">
        <el-card shadow="never" style="max-width: 720px" v-loading="loading">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <b>企业微信登录</b>
              <el-switch v-model="form.enabled" active-text="启用" />
            </div>
          </template>
          <el-form :model="form" label-width="110px">
            <el-form-item label="Corp ID">
              <el-input v-model="form.corp_id" placeholder="ww1234567890abcdef" />
            </el-form-item>
            <el-form-item label="Corp Secret">
              <el-input v-model="form.corp_secret" type="password" show-password />
            </el-form-item>
            <el-form-item label="Agent ID">
              <el-input v-model="form.agent_id" placeholder="1000002" />
            </el-form-item>
            <el-form-item>
              <div style="display: flex; gap: 10px">
                <el-button type="primary" :loading="saving" @click="save">保存</el-button>
                <el-button :loading="testing" @click="test">测试连接</el-button>
              </div>
            </el-form-item>
          </el-form>
          <el-alert style="margin-top: 6px" type="info" :closable="false"
            title="保存启用后, 登录页将出现「企业微信登录」按钮; 授权回调地址需配置为 {站点地址}/login" />
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="钉钉" name="dingtalk" disabled>
        <el-empty description="即将支持" />
      </el-tab-pane>
      <el-tab-pane label="飞书" name="feishu" disabled>
        <el-empty description="即将支持" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const tab = ref('wecom')
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const form = reactive({ enabled: false, corp_id: '', corp_secret: '', agent_id: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/auth-config')
    Object.assign(form, data.wecom)
  } finally {
    loading.value = false
  }
}

function payload() {
  return { ...form, corp_secret: form.corp_secret === '******' ? undefined : form.corp_secret }
}

async function save() {
  saving.value = true
  try {
    await api.put('/admin/auth-config/wecom', payload())
    ElMessage.success('企业微信配置已保存')
    auth.fetchOptions()
    await load()
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  try {
    const { data } = await api.post('/admin/auth-config/wecom/test', payload())
    data.ok ? ElMessage.success(data.message) : ElMessage.error(data.message)
  } catch { /* interceptor */ } finally {
    testing.value = false
  }
}

onMounted(load)
</script>
