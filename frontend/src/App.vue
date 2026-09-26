<template>
    <el-container class="app-container">
        <el-header class="header">
            <div class="header-content">
                <el-icon class="logo-icon"><VideoCamera /></el-icon>
                <h1>激光测振会议系统</h1>
                <span class="subtitle">Laser Vibrometry Spy System</span>
            </div>
            <el-menu 
                mode="horizontal" 
                :router="true" 
                :default-active="$route.path"
                class="nav-menu"
            >
                <el-menu-item index="/">
                    <el-icon><Monitor /></el-icon>
                    <span>首页</span>
                </el-menu-item>
                <el-menu-item index="/localization">
                    <el-icon><Location /></el-icon>
                    <span>声源定位</span>
                </el-menu-item>
                <el-menu-item index="/processing">
                    <el-icon><Upload /></el-icon>
                    <span>音频处理</span>
                </el-menu-item>
                <el-menu-item index="/transcripts">
                    <el-icon><Document /></el-icon>
                    <span>会议纪要</span>
                </el-menu-item>
            </el-menu>
        </el-header>
        
        <el-main class="main-content">
            <router-view />
        </el-main>
        
        <el-footer class="footer">
            <span>© 2026 Laser Vibrometry System - 仅限合法授权的安全测试使用</span>
        </el-footer>
    </el-container>
</template>

<script setup>
</script>

<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
}

.app-container {
    min-height: 100vh;
}

.header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-bottom: 1px solid #0f3460;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 30px;
    height: 80px;
}

.header-content {
    display: flex;
    align-items: center;
    gap: 15px;
}

.logo-icon {
    font-size: 32px;
    color: #e94560;
}

.header h1 {
    color: #ffffff;
    font-size: 22px;
    font-weight: 600;
}

.subtitle {
    color: #8892b0;
    font-size: 12px;
    margin-left: 10px;
}

.nav-menu {
    background: transparent;
    border: none;
}

.nav-menu .el-menu-item {
    color: #a8b2d1;
    border-bottom: 2px solid transparent;
}

.nav-menu .el-menu-item:hover {
    background: rgba(233, 69, 96, 0.1);
    color: #e94560;
}

.nav-menu .el-menu-item.is-active {
    color: #e94560;
    border-bottom-color: #e94560;
}

.main-content {
    background: #0a0a0f;
    padding: 30px;
}

.footer {
    background: #1a1a2e;
    color: #8892b0;
    text-align: center;
    font-size: 12px;
    border-top: 1px solid #0f3460;
}
</style>
