<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="brand-side">
      <div class="brand-mark">
        <span class="big-logo">P</span>
        <h1>PrjHub</h1>
        <p class="slogan">轻量级项目管理 · 审批流 · 代码仓库</p>
      </div>
      <ul class="features">
        <li><span class="dot" /><b>项目看板</b>任务全流程可视化拖拽</li>
        <li><span class="dot" /><b>可视化审批流</b>会签 / 或签 / 条件分支</li>
        <li><span class="dot" /><b>企业级认证</b>LDAP / 企业微信一键登录</li>
        <li><span class="dot" /><b>Git 仓库</b>项目创建自动初始化</li>
      </ul>
      <p class="copy">© 2026 PrjHub</p>
    </div>

    <!-- 右侧表单区 -->
    <div class="form-side">
      <div class="login-card">
        <h2>欢迎回来</h2>
        <p class="sub">登录你的工作空间</p>

        <el-form @submit.prevent="onLogin" size="large">
          <el-form-item>
            <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" autofocus />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" type="password" show-password placeholder="密码"
              :prefix-icon="Lock" @keyup.enter="onLogin" />
          </el-form-item>
          <el-button type="primary" size="large" style="width: 100%; height: 44px; font-size: 15px"
            :loading="loading" @click="onLogin">登 录</el-button>

          <el-divider v-if="auth.authOptions.wecom_enabled">
            <span style="font-size: 12px; color: var(--ph-text-secondary)">其他登录方式</span>
          </el-divider>
          <el-button v-if="auth.authOptions.wecom_enabled" size="large" style="width: 100%" @click="goWecom">
            <span class="wecom-icon">企</span> 企业微信登录
          </el-button>
          <p class="hint">
            支持本地账号{{ auth.authOptions.ldap_enabled ? ' / LDAP 域账号' : '' }}登录
          </p>
        </el-form>
      </div>
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
.login-page { height: 100%; display: flex; }

.brand-side {
  flex: 1.15; position: relative; display: flex; flex-direction: column; justify-content: center;
  padding: 0 8%;
  background:
    radial-gradient(ellipse 70% 55% at 85% 15%, rgba(64,158,255,.22) 0%, transparent 55%),
    radial-gradient(ellipse 55% 45% at 10% 90%, rgba(64,158,255,.10) 0%, transparent 55%),
    linear-gradient(160deg, #141a26 0%, #1a2233 55%, #16202e 100%);
  color: #fff; overflow: hidden;
}
.big-logo {
  width: 64px; height: 64px; border-radius: 18px;
  background: linear-gradient(135deg, var(--ph-primary) 0%, #2b6cb0 100%);
  font-size: 34px; font-weight: 800; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 10px 30px rgba(64,158,255,.4); margin-bottom: 18px;
}
.brand-mark h1 { font-size: 30px; letter-spacing: 1px; }
.slogan { color: #8b95a7; margin-top: 8px; font-size: 14px; }

.features { list-style: none; margin-top: 42px; display: grid; gap: 16px; }
.features li { display: flex; align-items: center; gap: 10px; color: #aab3c2; font-size: 13px; }
.features b { color: #e7ebf1; font-weight: 600; margin-right: 2px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ph-primary);
  box-shadow: 0 0 8px var(--ph-primary); flex-shrink: 0; }
.copy { position: absolute; bottom: 24px; left: 8%; color: #4c5566; font-size: 12px; }

.form-side {
  flex: 1; display: flex; align-items: center; justify-content: center;
  background: var(--ph-fill-blank, #fff);
}
.login-card { width: 360px; }
.login-card h2 { font-size: 24px; color: var(--ph-text-primary); }
.sub { color: var(--ph-text-secondary); font-size: 13px; margin: 6px 0 26px; }
.hint { margin-top: 18px; text-align: center; font-size: 12px; color: var(--ph-text-disabled); }
.wecom-icon {
  display: inline-block; width: 18px; height: 18px; line-height: 18px; border-radius: 4px;
  background: #0082ef; color: #fff; font-size: 12px; margin-right: 6px; text-align: center;
}

@media (max-width: 860px) { .brand-side { display: none; } }
</style>
