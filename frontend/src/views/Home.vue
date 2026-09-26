<template>
    <div class="home-container">
        <el-row :gutter="20">
            <el-col :span="24">
                <div class="hero-section">
                    <h2>激光测振会议系统</h2>
                    <p class="subtitle">Laser Vibrometry Spy System - 远程声波获取与会议纪要生成平台</p>
                    <el-tag type="warning" class="warning-tag">
                        <el-icon><Warning /></el-icon>
                        仅限合法授权的安全测试使用
                    </el-tag>
                </div>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="stats-row">
            <el-col :span="6">
                <el-card class="stat-card">
            <div class="stat-icon blue">
                <el-icon><Location /></el-icon>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{{ stats.localizationCount }}</div>
                        <div class="stat-label">声源定位任务</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card class="stat-card">
                    <div class="stat-icon green">
                        <el-icon><Headset /></el-icon>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{{ stats.processingCount }}</div>
                        <div class="stat-label">音频处理任务</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card class="stat-card">
                    <div class="stat-icon purple">
                        <el-icon><Document /></el-icon>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{{ stats.transcriptCount }}</div>
                        <div class="stat-label">生成会议纪要</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card class="stat-card">
                    <div class="stat-icon orange">
                        <el-icon><Cpu /></el-icon>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{{ modelStatus }}</div>
                        <div class="stat-label">AI模型状态</div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="features-row">
            <el-col :span="12">
                <el-card class="feature-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><VideoCamera /></el-icon>
                            <span>系统功能</span>
                        </div>
                    </template>
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="激光测振">
                            通过激光测振仪远程获取窗户振动信号
                        </el-descriptions-item>
                        <el-descriptions-item label="极低信噪比处理">
                            librosa极端增强算法处理低质量音频
                        </el-descriptions-item>
                        <el-descriptions-item label="去卷积还原">
                            高级信号处理还原原始语音
                        </el-descriptions-item>
                        <el-descriptions-item label="Whisper转写">
                            OpenAI Whisper进行高精度语音转文字
                        </el-descriptions-item>
                        <el-descriptions-item label="说话人分离">
                            pyannote.audio区分不同发言人
                        </el-descriptions-item>
                        <el-descriptions-item label="AI摘要">
                            GPT生成模糊但可用的会议摘要
                        </el-descriptions-item>
                        <el-descriptions-item label="加密邮件">
                            Markdown加密发送会议纪要
                        </el-descriptions-item>
                    </el-descriptions>
                </el-card>
            </el-col>
            <el-col :span="12">
                <el-card class="feature-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Operation /></el-icon>
                            <span>快速操作</span>
                        </div>
                    </template>
                    <div class="quick-actions">
                        <el-button type="primary" size="large" @click="$router.push('/localization')">
                            <el-icon><Location /></el-icon>
                            开始声源定位
                        </el-button>
                        <el-button type="success" size="large" @click="$router.push('/processing')">
                            <el-icon><Upload /></el-icon>
                            上传音频处理
                        </el-button>
                        <el-button type="warning" size="large" @click="$router.push('/transcripts')">
                            <el-icon><Document /></el-icon>
                            查看会议纪要
                        </el-button>
                    </div>
                    <el-divider />
                    <div class="system-info">
                        <h4>系统状态</h4>
                        <el-tag :type="apiStatus.type" class="status-tag">
                            API: {{ apiStatus.text }}
                        </el-tag>
                        <el-tag :type="wsStatus.type" class="status-tag">
                            WebSocket: {{ wsStatus.text }}
                        </el-tag>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="notice-card">
                    <el-alert
                        title="法律声明"
                        type="warning"
                        :closable="false"
                        show-icon
                    >
                        <template #default>
                            <p>本系统仅用于合法授权的安全测试目的。使用者必须遵守所有适用的法律法规。</p>
                            <p>未经授权对他人进行监听、录音或获取通信内容是违法行为，将承担相应的法律责任。</p>
                        </template>
                    </el-alert>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({
    localizationCount: 0,
    processingCount: 0,
    transcriptCount: 0
})

const modelStatus = ref('检测中')
const apiStatus = ref({ type: 'info', text: '检查中' })
const wsStatus = ref({ type: 'info', text: '未连接' })

onMounted(async () => {
    try {
        const response = await axios.get('/api/health')
        if (response.data.status === 'healthy') {
            apiStatus.value = { type: 'success', text: '正常' }
            const models = response.data.models_loaded
            const loadedCount = Object.values(models).filter(v => v).length
            modelStatus.value = `${loadedCount}/3 已加载`
        }
    } catch (e) {
        apiStatus.value = { type: 'error', text: '未连接' }
        modelStatus.value = '未连接'
    }
})
</script>

<style scoped>
.home-container {
    max-width: 1400px;
    margin: 0 auto;
}

.hero-section {
    text-align: center;
    padding: 40px 0;
}

.hero-section h2 {
    font-size: 36px;
    color: #ffffff;
    margin-bottom: 10px;
}

.hero-section .subtitle {
    color: #8892b0;
    font-size: 16px;
    margin-bottom: 20px;
}

.warning-tag {
    font-size: 14px;
}

.stats-row {
    margin-bottom: 30px;
}

.stat-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    display: flex;
    align-items: center;
    padding: 20px;
}

.stat-card :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px;
}

.stat-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
}

.stat-icon.blue {
    background: rgba(64, 158, 255, 0.2);
    color: #409eff;
}

.stat-icon.green {
    background: rgba(103, 194, 58, 0.2);
    color: #67c23a;
}

.stat-icon.purple {
    background: rgba(155, 89, 182, 0.2);
    color: #9b59b6;
}

.stat-icon.orange {
    background: rgba(230, 162, 60, 0.2);
    color: #e6a23c;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #ffffff;
}

.stat-label {
    color: #8892b0;
    font-size: 14px;
}

.features-row {
    margin-bottom: 30px;
}

.feature-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    height: 100%;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;
    color: #e94560;
}

.quick-actions {
    display: flex;
    flex-direction: column;
    gap: 15px;
    padding: 20px 0;
}

.quick-actions .el-button {
    width: 100%;
    justify-content: center;
}

.system-info h4 {
    color: #ffffff;
    margin-bottom: 15px;
}

.status-tag {
    margin-right: 10px;
}

.notice-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
}

:deep(.el-descriptions) {
    --el-descriptions-item-label-color: #8892b0;
    --el-descriptions-item-content-color: #e0e0e0;
    --el-border-color-lighter: #0f3460;
}

:deep(.el-descriptions__body) {
    background: transparent;
}

:deep(.el-descriptions__cell) {
    border-color: #0f3460;
}
</style>
