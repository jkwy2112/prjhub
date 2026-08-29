<template>
  <div class="admin-full">
    <header class="admin-header">
      <div class="header-left">
        <span class="logo">P</span>
        <b>PrjHub · 系统管理</b>
      </div>
      <div class="header-right">
        <el-button text :icon="Back" @click="$router.push('/dashboard')">返回工作台</el-button>
        <el-dropdown @command="onCommand">
          <span class="user-chip">
            <el-avatar :size="28" style="background: #409EFF">{{ avatarText }}</el-avatar>
            <span class="user-name">{{ auth.displayName }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="workbench">返回工作台</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="admin-body">
      <el-menu :default-active="$route.path" router class="admin-menu" background-color="#001529"
        text-color="#a6adb4" active-text-color="#fff">
        <el-menu-item index="/admin/overview"><el-icon><Odometer /></el-icon>系统概览</el-menu-item>
        <el-menu-item index="/admin/users"><el-icon><User /></el-icon>用户管理</el-menu-item>
        <el-menu-item index="/admin/workflows"><el-icon><Share /></el-icon>工作流</el-menu-item>
        <el-sub-menu index="integrations">
          <template #title><el-icon><Link /></el-icon>集成配置</template>
          <el-menu-item index="/admin/auth/ldap">LDAP 认证</el-menu-item>
          <el-menu-item index="/admin/im/wecom">IM 配置</el-menu-item>
        </el-sub-menu>
      </el-menu>
      <main class="admin-main"><router-view /></main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Odometer, User, Share, Link, ArrowDown, Back } from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const avatarText = computed(() => auth.displayName.slice(0, 1).toUpperCase())

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.replace('/login')
  } else if (cmd === 'workbench') {
    router.push('/dashboard')
  }
}
</script>

<style scoped>
.admin-full { display: flex; flex-direction: column; height: 100vh; }
.admin-header {
  height: 56px; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; background: #001529; color: #fff;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.logo {
  width: 30px; height: 30px; border-radius: 8px; background: #409EFF;
  font-weight: 700; font-size: 18px; text-align: center; line-height: 30px;
}
.header-right { display: flex; align-items: center; gap: 12px; }
.header-right :deep(.el-button) { color: #a6adb4; }
.header-right :deep(.el-button:hover) { color: #fff; }
.user-chip { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.user-name { font-size: 14px; color: #e5eaf3; }
.admin-body { flex: 1; display: flex; min-height: 0; }
.admin-menu { width: 200px; border-right: none; flex-shrink: 0; }
.admin-main { flex: 1; padding: 20px; overflow: auto; background: #f5f7fa; }
</style>
