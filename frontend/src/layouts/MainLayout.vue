<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="brand" @click="$router.push('/dashboard')">
        <span class="brand-logo">P</span>
        <span class="brand-name">PrjHub</span>
      </div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#a6adb4"
        active-text-color="#fff" class="menu">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon>仪表盘</el-menu-item>
        <el-menu-item index="/projects"><el-icon><Folder /></el-icon>项目</el-menu-item>
        <el-menu-item index="/my-tasks"><el-icon><List /></el-icon>我的任务</el-menu-item>
      </el-menu>
      <div class="sidebar-footer">v0.1.0</div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ pageTitle }}</div>
        <el-dropdown @command="onCommand">
          <span class="user-chip">
            <el-avatar :size="30" style="background: #409EFF">{{ avatarText }}</el-avatar>
            <span class="user-name">{{ auth.displayName }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Odometer, Folder, List, ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const pageTitle = computed(() => ({ '/dashboard': '仪表盘', '/projects': '项目', '/my-tasks': '我的任务' }[route.path] || 'PrjHub'))
const avatarText = computed(() => auth.displayName.slice(0, 1).toUpperCase())

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.replace('/login')
  }
}
</script>

<style scoped>
.layout { height: 100%; }
.sidebar { display: flex; flex-direction: column; background: #001529; }
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 20px; cursor: pointer;
}
.brand-logo {
  width: 34px; height: 34px; border-radius: 8px; background: #409EFF;
  color: #fff; font-weight: 700; font-size: 20px; text-align: center; line-height: 34px;
}
.brand-name { color: #fff; font-size: 18px; font-weight: 600; }
.menu { border-right: none; flex: 1; }
.sidebar-footer { padding: 12px 20px; color: #485661; font-size: 12px; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #e4e7ed;
}
.header-title { font-size: 16px; font-weight: 600; color: #303133; }
.user-chip { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.user-name { font-size: 14px; color: #303133; }
.main { padding: 20px; overflow: auto; }
</style>
