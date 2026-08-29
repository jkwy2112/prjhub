<template>
  <el-card shadow="never" style="max-width: 720px" v-loading="loading">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>LDAP 域认证</b>
        <el-switch v-model="form.enabled" active-text="启用" />
      </div>
    </template>
    <el-form :model="form" label-width="110px" size="default">
      <el-form-item label="服务器">
        <el-input v-model="form.server" placeholder="ldap://ldap.corp.com:389" />
      </el-form-item>
      <el-form-item label="启用 SSL">
        <el-switch v-model="form.use_ssl" />
      </el-form-item>
      <el-form-item label="Bind DN">
        <el-input v-model="form.bind_dn" placeholder="cn=admin,dc=corp,dc=com" />
      </el-form-item>
      <el-form-item label="Bind 密码">
        <el-input v-model="form.bind_password" type="password" show-password placeholder="服务账号密码" />
      </el-form-item>
      <el-form-item label="搜索基准">
        <el-input v-model="form.search_base" placeholder="ou=people,dc=corp,dc=com" />
      </el-form-item>
      <el-form-item label="搜索过滤器">
        <el-input v-model="form.search_filter" placeholder="(uid={login}) — AD 用 (sAMAccountName={login})" />
      </el-form-item>
      <el-row>
        <el-col :span="8">
          <el-form-item label="用户名属性">
            <el-input v-model="form.attr_username" placeholder="uid" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="姓名属性">
            <el-input v-model="form.attr_display_name" placeholder="cn" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="邮箱属性">
            <el-input v-model="form.attr_email" placeholder="mail" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item>
        <div style="display: flex; gap: 10px">
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button :loading="testing" @click="test">测试连接</el-button>
        </div>
      </el-form-item>
    </el-form>
    <el-alert type="info" :closable="false"
      title="启用后, 用户使用域账号密码登录, 本地校验失败自动走 LDAP; 首次登录自动创建账号并同步姓名/邮箱" />
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const form = reactive({
  enabled: false, server: '', use_ssl: false, bind_dn: '', bind_password: '',
  search_base: '', search_filter: '(uid={login})', attr_username: 'uid',
  attr_display_name: 'cn', attr_email: 'mail',
})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/auth-config')
    Object.assign(form, data.ldap)
  } finally {
    loading.value = false
  }
}

function payload() {
  return { ...form, bind_password: form.bind_password === '******' ? undefined : form.bind_password }
}

async function save() {
  saving.value = true
  try {
    await api.put('/admin/auth-config/ldap', payload())
    ElMessage.success('LDAP 配置已保存')
    await load()
  } catch { /* interceptor */ } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  try {
    const { data } = await api.post('/admin/auth-config/ldap/test', payload())
    data.ok ? ElMessage.success(data.message) : ElMessage.error(data.message)
  } catch { /* interceptor */ } finally {
    testing.value = false
  }
}

onMounted(load)
</script>
