<template>
  <div class="admin-page">
    <el-menu :default-active="$route.path" router mode="horizontal" class="admin-nav"
      background-color="#fff" text-color="#606266">
      <el-menu-item index="/admin/overview">系统概览</el-menu-item>
      <el-menu-item index="/admin/users">用户管理</el-menu-item>
      <el-menu-item index="/admin/workflows">工作流</el-menu-item>
      <el-menu-item index="/admin/flows">审批流程</el-menu-item>
      <el-sub-menu index="integrations">
        <template #title>集成配置</template>
        <el-menu-item index="/admin/auth/ldap">LDAP 认证</el-menu-item>
        <el-menu-item index="/admin/im/wecom">IM 配置 · 企业微信</el-menu-item>
      </el-sub-menu>
    </el-menu>
    <div class="admin-content"><router-view /></div>
  </div>
</template>

<style scoped>
.admin-page { min-height: calc(100vh - 60px - 40px); display: flex; flex-direction: column; }
.admin-nav {
  border-bottom: 1px solid #e4e7ed; border-radius: 8px 8px 0 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.admin-content { flex: 1; padding-top: 16px; }
</style>
