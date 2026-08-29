<template>
  <div class="admin-layout">
    <el-menu :default-active="$route.path" router class="admin-menu" background-color="#001529"
      text-color="#a6adb4" active-text-color="#fff">
      <div class="admin-title">系统管理</div>
      <el-menu-item index="/admin/overview"><el-icon><Odometer /></el-icon>系统概览</el-menu-item>
      <el-menu-item index="/admin/users"><el-icon><User /></el-icon>用户管理</el-menu-item>
      <el-menu-item index="/admin/workflows"><el-icon><Share /></el-icon>工作流</el-menu-item>
      <el-sub-menu index="integrations">
        <template #title><el-icon><Link /></el-icon>集成配置</template>
        <el-menu-item index="/admin/auth/ldap">LDAP 认证</el-menu-item>
        <el-menu-item index="/admin/im/wecom">IM 配置</el-menu-item>
      </el-sub-menu>
    </el-menu>
    <div class="admin-main"><router-view /></div>
  </div>
</template>

<script setup>
import { Odometer, User, Share, Link } from '@element-plus/icons-vue'
</script>

<style scoped>
.admin-layout { display: flex; height: calc(100vh - 60px); margin: -20px; }
.admin-menu { width: 200px; border-right: none; }
.admin-title {
  color: #fff; font-size: 13px; font-weight: 600;
  padding: 14px 20px 10px; letter-spacing: 1px;
}
.admin-main { flex: 1; padding: 20px; overflow: auto; background: #f5f7fa; }
</style>
