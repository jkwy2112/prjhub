<template>
  <router-view />
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  font-size: var(--ph-font-base);
  color: var(--ph-text-primary);
  background: var(--ph-bg-page);
  -webkit-font-smoothing: antialiased;
}
/* Element Plus 阴影/圆角统一 (一致原则) */
.el-card { border-radius: var(--ph-radius-lg); border: 1px solid var(--ph-border-lighter); }
.el-button { border-radius: var(--ph-radius-base); }
.el-dialog { border-radius: var(--ph-radius-lg); }
.el-drawer { border-radius: var(--ph-radius-lg) 0 0 var(--ph-radius-lg); }
/* 统一细滚动条 (效率原则: 不抢注意力) */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: var(--ph-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--ph-text-placeholder); }
::-webkit-scrollbar-track { background: transparent; }
/* 页面切换过渡 (反馈原则) */
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
