<template>
  <el-container class="layout">
    <el-aside width="216px" class="sidebar">
      <div class="brand" @click="$router.push('/dashboard')">
        <span class="brand-logo">P</span>
        <div class="brand-text">
          <b>PrjHub</b>
          <span>项目 · 审批 · 协作</span>
        </div>
      </div>

      <el-menu :default-active="$route.path" router background-color="transparent" text-color="#9aa3af"
        active-text-color="#ffffff" class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-foot">
        <div class="foot-card">
          <el-icon :size="14"><InfoFilled /></el-icon>
          <span>PrjHub v0.1.0</span>
        </div>
      </div>
    </el-aside>

    <el-container class="right-col">
      <el-header class="header">
        <div class="header-left">
          <h2 class="page-title">{{ pageTitle }}</h2>
          <span class="page-sub">{{ pageSub }}</span>
        </div>
        <el-dropdown @command="onCommand" trigger="click">
          <span class="user-chip">
            <el-avatar :size="32" style="background: var(--ph-primary)">{{ avatarText }}</el-avatar>
            <div class="user-meta">
              <b>{{ auth.displayName }}</b>
              <span>{{ auth.user?.is_superuser ? '管理员' : '成员' }}</span>
            </div>
            <el-icon style="color: var(--ph-text-secondary)"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                {{ auth.user?.email || auth.user?.username }}
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Odometer, Folder, List, ArrowDown, Setting, Stamp, InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = computed(() => {
  const list = [
    { path: '/dashboard', label: '仪表盘', icon: markRaw(Odometer) },
    { path: '/projects', label: '项目', icon: markRaw(Folder) },
    { path: '/my-tasks', label: '我的任务', icon: markRaw(List) },
    { path: '/approvals', label: '审批中心', icon: markRaw(Stamp) },
  ]
  if (auth.user?.is_superuser) {
    list.push({ path: '/admin', label: '系统管理', icon: markRaw(Setting) })
  }
  return list
})

const PAGE_META = {
  '/dashboard': ['仪表盘', '总览你的工作与动态'],
  '/projects': ['项目', '管理项目、任务与代码仓库'],
  '/my-tasks': ['我的任务', '所有分配给你的任务'],
  '/approvals': ['审批中心', '待办审批与我发起的流程'],
  '/admin': ['系统管理', '用户、流程与集成配置'],
}
const pageTitle = computed(() => (PAGE_META[route.path] || PAGE_META[route.matched[0]?.path] || ['PrjHub'])[0])
const pageSub = computed(() => (PAGE_META[route.path] || PAGE_META[route.matched[0]?.path] || ['', ''])[1])
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
.sidebar {
  display: flex; flex-direction: column;
  background: linear-gradient(180deg, #1f2430 0%, #171b24 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.04);
}
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 18px 14px; cursor: pointer;
}
.brand-logo {
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, var(--ph-primary) 0%, var(--ph-primary-dark-2) 100%);
  color: #fff; font-weight: 800; font-size: 19px; text-align: center; line-height: 36px;
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.35);
}
.brand-text b { display: block; color: #fff; font-size: 15px; letter-spacing: .3px; }
.brand-text span { font-size: 11px; color: #6b7280; letter-spacing: .5px; }

.menu { border-right: none; flex: 1; padding: 6px 10px; }
.menu :deep(.el-menu-item) {
  height: 44px; margin-bottom: 2px; border-radius: 8px; font-size: 14px;
  transition: all .15s;
}
.menu :deep(.el-menu-item:hover) { background: rgba(255, 255, 255, 0.05); color: #fff; }
.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, var(--ph-primary) 0%, var(--ph-primary-dark-2) 100%);
  color: #fff; box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}
.menu :deep(.el-menu-item .el-icon) { margin-right: 8px; }

.sidebar-foot { padding: 12px 16px; }
.foot-card {
  display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 7px 0; border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  color: #565d6b; font-size: 11px;
}

.right-col { flex-direction: column; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--ph-fill-blank, #fff);
  border-bottom: 1px solid var(--ph-border-lighter);
  box-shadow: none; height: 58px; z-index: 5;
}
.header-left { display: flex; align-items: baseline; gap: 10px; }
.page-title { font-size: 16px; font-weight: 700; color: var(--ph-text-primary); }
.page-sub { font-size: 12px; color: var(--ph-text-secondary); }

.user-chip {
  display: flex; align-items: center; gap: 9px; cursor: pointer;
  padding: 4px 10px 4px 4px; border-radius: 999px; transition: background .15s;
}
.user-chip:hover { background: var(--ph-fill-light); }
.user-meta { display: flex; flex-direction: column; line-height: 1.25; }
.user-meta b { font-size: 13px; color: var(--ph-text-primary); }
.user-meta span { font-size: 11px; color: var(--ph-text-secondary); }

.main { padding: var(--ph-space-5); overflow: auto; background: var(--ph-bg-page); }

.page-enter-active, .page-leave-active { transition: opacity .16s ease, transform .16s ease; }
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
