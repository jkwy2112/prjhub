<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="logo">P</div>
        <h1>PrjHub</h1>
        <p>轻量级项目管理系统 · 任务看板 · 代码仓库</p>
      </div>
      <el-form @submit.prevent="onLogin" size="large">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" autofocus />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" show-password placeholder="密码"
            :prefix-icon="Lock" @keyup.enter="onLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onLogin">
          登 录
        </el-button>
        <el-divider v-if="auth.wecom_enabled">
          <span style="font-size: 12px; color: #999">其他登录方式</span>
        </el-divider>
        <el-button v-if="auth.wecom_enabled" size="large" style="width: 100%" @click="goWecom">
          <span class="wecom-icon">企</span> 企业微信登录
        </el-button>
        <p class="hint">支持本地账号{{ auth.ldap_enabled ? ' / LDAP 域账号' : '' }}登录</p>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

onMounted(() => {
  auth.fetchOptions()
  const code = route.query.code
  if (code && String(route.query.state) === 'wecom') {
    loading.value = true
    auth.wecomLogin(String(code)).then(() => {
      ElMessage.success('企业微信登录成功')
      router.replace(route.query.redirect || '/dashboard')
    }).finally(() => (loading.value = false))
  }
})

async function onLogin() {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.replace(route.query.redirect || '/dashboard')
  } catch { /* interceptor shows error */ } finally {
    loading.value = false
  }
}

async function goWecom() {
  const redirectUri = `${location.origin}/login`
  const url = await auth.wecomUrl(redirectUri)
  location.href = url
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d2b64 0%, #409EFF6b 100%), #1d2b64;
}
.login-card {
  width: 380px;
  padding: 40px 36px 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
}
.login-brand { text-align: center; margin-bottom: 28px; }
.logo {
  width: 56px; height: 56px; margin: 0 auto 12px;
  border-radius: 14px; background: #409EFF; color: #fff;
  font-size: 32px; font-weight: 700; line-height: 56px;
}
.login-brand h1 { font-size: 22px; color: #303133; }
.login-brand p { font-size: 12px; color: #909399; margin-top: 6px; }
.hint { margin-top: 16px; text-align: center; font-size: 12px; color: #c0c4cc; }
.wecom-icon {
  display: inline-block; width: 18px; height: 18px; line-height: 18px; border-radius: 4px;
  background: #0082ef; color: #fff; font-size: 12px; margin-right: 6px;
}
</style>
