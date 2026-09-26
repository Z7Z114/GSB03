<template>
    <div class="processing-container">
        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="header-card">
                    <div class="header-content">
                        <div>
                            <h2>音频处理中心</h2>
                            <p class="subtitle">Audio Processing Center - 激光测振音频增强与转写</p>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="8">
                <el-card class="upload-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Upload /></el-icon>
                            <span>上传振动数据</span>
                        </div>
                    </template>
                    
                    <el-upload
                        drag
                        action="/api/process/audio"
                        :auto-upload="false"
                        :show-file-list="true"
                        :file-list="fileList"
                        @change="handleFileChange"
                        :before-upload="beforeUpload"
                        accept=".wav,.mp3,.flac,.aac"
                    >
                        <el-icon class="upload-icon"><UploadFilled /></el-icon>
                        <div class="el-upload__text">拖放激光振动数据文件到此处</div>
                        <div class="el-upload__text"><em>支持 WAV, MP3, FLAC, AAC 格式</em></div>
                        <template #tip>
                            <div class="el-upload__tip">
                                建议上传48kHz采样率的单声道音频文件
                            </div>
                        </template>
                    </el-upload>

                    <el-divider />

                    <div class="processing-options">
                        <h4>处理选项</h4>
                        <el-form :model="options" label-width="120px">
                            <el-form-item label="语言">
                                <el-select v-model="options.language">
                                    <el-option label="中文" value="zh" />
                                    <el-option label="英文" value="en" />
                                    <el-option label="自动检测" value="auto" />
                                </el-select>
                            </el-form-item>
                            <el-form-item label="预计人数">
                                <el-input-number 
                                    v-model="options.num_speakers" 
                                    :min="1" 
                                    :max="10" 
                                    :controls="true"
                                    placeholder="可选"
                                />
                            </el-form-item>
                            <el-form-item label="生成摘要">
                                <el-switch v-model="options.generate_summary" />
                            </el-form-item>
                            <el-form-item label="发送邮件">
                                <el-switch v-model="options.send_email" />
                            </el-form-item>
                            <el-form-item v-if="options.send_email" label="收件人">
                                <el-select 
                                    v-model="options.recipient_emails" 
                                    multiple 
                                    filterable 
                                    allow-create
                                    placeholder="输入邮箱地址"
                                    style="width: 100%"
                                >
                                </el-select>
                            </el-form-item>
                        </el-form>
                    </div>

                    <el-button 
                        type="primary" 
                        size="large" 
                        style="width: 100%; margin-top: 20px"
                        :disabled="fileList.length === 0"
                        :loading="isProcessing"
                        @click="startProcessing"
                    >
                        <el-icon><VideoPlay /></el-icon>
                        开始处理
                    </el-button>
                </el-card>

                <el-card class="pipeline-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Connection /></el-icon>
                            <span>处理流程</span>
                        </div>
                    </template>
                    <div class="pipeline-steps">
                        <div 
                            v-for="(step, index) in pipelineSteps" 
                            :key="index"
                            class="pipeline-step"
                            :class="getStepClass(step)"
                        >
                            <div class="step-icon">
                                <el-icon v-if="step.status === 'done'"><Check /></el-icon>
                                <el-icon v-else-if="step.status === 'active'" class="loading"><Loading /></el-icon>
                                <span v-else>{{ index + 1 }}</span>
                            </div>
                            <div class="step-info">
                                <div class="step-name">{{ step.name }}</div>
                                <div class="step-desc">{{ step.description }}</div>
                            </div>
                        </div>
                    </div>
                </el-card>
            </el-col>

            <el-col :span="16">
                <el-card class="progress-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><DataAnalysis /></el-icon>
                            <span>处理进度</span>
                            <el-tag v-if="currentTask" :type="getTaskTagType(currentTask.status)">
                                {{ getTaskStatusText(currentTask.status) }}
                            </el-tag>
                        </div>
                    </template>

                    <div v-if="!currentTask" class="no-task">
                        <el-empty description="暂无处理任务" :image-size="120" />
                    </div>

                    <div v-else class="task-content">
                        <el-progress 
                            :percentage="currentTask.progress" 
                            :status="currentTask.status === 'failed' ? 'exception' : ''"
                            :stroke-width="12"
                            class="main-progress"
                        />
                        <p class="progress-message">{{ currentTask.message }}</p>

                        <el-tabs v-if="currentTask.result" class="result-tabs">
                            <el-tab-pane label="波形预览" name="waveform">
                                <div class="waveform-container">
                                    <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
                                </div>
                            </el-tab-pane>
                            <el-tab-pane label="频谱分析" name="spectrum">
                                <div class="spectrum-container">
                                    <canvas ref="spectrumCanvas" class="spectrum-canvas"></canvas>
                                </div>
                            </el-tab-pane>
                            <el-tab-pane label="转写结果" name="transcript">
                                <div class="transcript-content">
                                    <div v-if="currentTask.result.transcript" class="transcript-text">
                                        <h4>完整转写</h4>
                                        <p>{{ currentTask.result.transcript.full_text }}</p>
                                        
                                        <el-divider />
                                        
                                        <h4>按发言者</h4>
                                        <div class="speaker-segments">
                                            <div 
                                                v-for="(seg, index) in currentTask.result.transcript.segments" 
                                                :key="index"
                                                class="segment-item"
                                            >
                                                <el-tag :type="getSpeakerTagType(seg.speaker)" class="speaker-tag">
                                                    {{ seg.speaker }}
                                                </el-tag>
                                                <span class="segment-time">[{{ formatTime(seg.start) }} - {{ formatTime(seg.end) }}]</span>
                                                <span class="segment-text">{{ seg.text }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-else class="no-result">
                                        转写结果生成中...
                                    </div>
                                </div>
                            </el-tab-pane>
                            <el-tab-pane label="AI摘要" name="summary">
                                <div v-if="currentTask.result.summary" class="summary-content">
                                    <el-descriptions :column="2" border>
                                        <el-descriptions-item label="会议主题">
                                            {{ currentTask.result.summary.summary.title }}
                                        </el-descriptions-item>
                                        <el-descriptions-item label="会议日期">
                                            {{ currentTask.result.summary.summary.date }}
                                        </el-descriptions-item>
                                        <el-descriptions-item label="参会人员">
                                            {{ currentTask.result.summary.summary.participants?.join(', ') }}
                                        </el-descriptions-item>
                                        <el-descriptions-item label="置信度">
                                            {{ currentTask.result.summary.summary.confidence_note }}
                                        </el-descriptions-item>
                                    </el-descriptions>
                                    
                                    <el-divider />
                                    
                                    <h4>讨论议题</h4>
                                    <el-tag 
                                        v-for="(topic, index) in currentTask.result.summary.summary.key_topics" 
                                        :key="index"
                                        type="info"
                                        class="topic-tag"
                                    >
                                        {{ topic }}
                                    </el-tag>
                                    
                                    <el-divider />
                                    
                                    <h4>重要决定</h4>
                                    <ul>
                                        <li v-for="(decision, index) in currentTask.result.summary.summary.decisions" :key="index">
                                            {{ decision }}
                                        </li>
                                    </ul>
                                    
                                    <el-divider />
                                    
                                    <h4>会议摘要</h4>
                                    <p>{{ currentTask.result.summary.summary.summary }}</p>
                                </div>
                                <div v-else class="no-result">
                                    {{ options.generate_summary ? '摘要生成中...' : '未开启摘要生成' }}
                                </div>
                            </el-tab-pane>
                        </el-tabs>

                        <div v-if="currentTask.result" class="download-section">
                            <el-divider />
                            <h4>下载结果</h4>
                            <div class="download-buttons">
                                <el-button type="primary" @click="downloadResult('markdown')">
                                    <el-icon><Download /></el-icon>
                                    下载 Markdown
                                </el-button>
                                <el-button type="success" @click="downloadResult('json')">
                                    <el-icon><Download /></el-icon>
                                    下载 JSON 数据
                                </el-button>
                            </div>
                        </div>
                    </div>
                </el-card>

                <el-card class="tasks-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><List /></el-icon>
                            <span>历史任务</span>
                            <el-button size="small" @click="refreshTasks">
                                <el-icon><Refresh /></el-icon>
                                刷新
                            </el-button>
                        </div>
                    </template>
                    <el-table :data="taskList" style="width: 100%" max-height="300">
                        <el-table-column prop="task_id" label="任务ID" width="200" show-overflow-tooltip />
                        <el-table-column prop="status" label="状态" width="100">
                            <template #default="scope">
                                <el-tag :type="getTaskTagType(scope.row.status)">
                                    {{ getTaskStatusText(scope.row.status) }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="progress" label="进度" width="120">
                            <template #default="scope">
                                <el-progress :percentage="scope.row.progress" :stroke-width="8" />
                            </template>
                        </el-table-column>
                        <el-table-column prop="message" label="消息" show-overflow-tooltip />
                        <el-table-column prop="created_at" label="创建时间" width="180" show-overflow-tooltip />
                        <el-table-column label="操作" width="80">
                            <template #default="scope">
                                <el-button 
                                    type="primary" 
                                    size="small" 
                                    link
                                    @click="viewTask(scope.row)"
                                >
                                    查看
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import {
    Upload,
    UploadFilled,
    VideoPlay,
    Connection,
    Check,
    Loading,
    DataAnalysis,
    Download,
    List,
    Refresh
} from '@element-plus/icons-vue'

const fileList = ref([])
const isProcessing = ref(false)
const currentTask = ref(null)
const taskList = ref([])
const waveformCanvas = ref(null)
const spectrumCanvas = ref(null)

const options = reactive({
    language: 'zh',
    num_speakers: null,
    generate_summary: true,
    send_email: false,
    recipient_emails: []
})

const pipelineSteps = reactive([
    { name: '数据加载', description: '读取并解析振动数据', status: 'pending' },
    { name: '音频增强', description: 'librosa极端降噪与增强', status: 'pending' },
    { name: '去卷积', description: '反向卷积还原原始语音', status: 'pending' },
    { name: '语音转写', description: 'Whisper语音转文字', status: 'pending' },
    { name: '说话人分离', description: 'pyannote区分发言人', status: 'pending' },
    { name: 'AI摘要', description: 'OpenAI生成会议摘要', status: 'pending' },
    { name: '加密输出', description: 'Markdown加密与邮件发送', status: 'pending' }
])

let pollInterval = null

const beforeUpload = (file) => {
    const validTypes = ['audio/wav', 'audio/mp3', 'audio/flac', 'audio/aac', 'audio/x-wav', 'audio/mpeg']
    const isAudio = validTypes.includes(file.type) || file.name.match(/\.(wav|mp3|flac|aac)$/i)
    if (!isAudio) {
        ElMessage.error('请上传音频文件!')
        return false
    }
    const isLt100M = file.size / 1024 / 1024 < 100
    if (!isLt100M) {
        ElMessage.error('文件大小不能超过 100MB!')
        return false
    }
    return true
}

const handleFileChange = (file, fileListRef) => {
    fileList.value = fileListRef
}

const startProcessing = async () => {
    if (fileList.value.length === 0) {
        ElMessage.warning('请先上传音频文件')
        return
    }

    isProcessing.value = true
    
    pipelineSteps.forEach(step => step.status = 'pending')
    
    try {
        const formData = new FormData()
        formData.append('file', fileList.value[0].raw)
        formData.append('num_speakers', options.num_speakers || '')
        formData.append('language', options.language)
        formData.append('generate_summary', options.generate_summary)
        formData.append('send_email', options.send_email)
        if (options.send_email && options.recipient_emails.length > 0) {
            formData.append('recipient_emails', JSON.stringify(options.recipient_emails))
        }

        const response = await axios.post('/api/process/audio', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })

        currentTask.value = response.data
        startPolling(currentTask.value.task_id)

    } catch (e) {
        ElMessage.error('处理启动失败: ' + (e.response?.data?.detail || e.message))
        isProcessing.value = false
    }
}

const startPolling = (taskId) => {
    if (pollInterval) clearInterval(pollInterval)
    
    pollInterval = setInterval(async () => {
        try {
            const response = await axios.get(`/api/tasks/${taskId}`)
            currentTask.value = response.data
            
            updatePipelineSteps(response.data)
            
            if (response.data.status === 'completed' || response.data.status === 'failed') {
                clearInterval(pollInterval)
                isProcessing.value = false
                
                if (response.data.status === 'completed') {
                    ElMessage.success('处理完成')
                    if (response.data.result) {
                        drawWaveform()
                        drawSpectrum()
                    }
                } else {
                    ElMessage.error('处理失败: ' + response.data.message)
                }
                
                refreshTasks()
            }
        } catch (e) {
            console.error('Polling error:', e)
        }
    }, 2000)
}

const updatePipelineSteps = (task) => {
    const progress = task.progress
    
    if (progress >= 10) pipelineSteps[0].status = 'done'
    if (progress >= 30) pipelineSteps[1].status = 'done'
    if (progress >= 40) pipelineSteps[2].status = 'done'
    if (progress >= 50) pipelineSteps[3].status = 'done'
    if (progress >= 60) pipelineSteps[4].status = 'done'
    if (progress >= 85) pipelineSteps[5].status = 'done'
    if (progress >= 100) pipelineSteps[6].status = 'done'
    
    const activeIndex = Math.floor(progress / 15)
    if (activeIndex < 7 && pipelineSteps[activeIndex].status === 'pending') {
        pipelineSteps[activeIndex].status = 'active'
    }
}

const getStepClass = (step) => {
    return {
        'done': step.status === 'done',
        'active': step.status === 'active',
        'pending': step.status === 'pending'
    }
}

const getTaskTagType = (status) => {
    const types = {
        'queued': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
    }
    return types[status] || 'info'
}

const getTaskStatusText = (status) => {
    const texts = {
        'queued': '排队中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败'
    }
    return texts[status] || status
}

const getSpeakerTagType = (speaker) => {
    const types = ['primary', 'success', 'warning', 'info', 'danger']
    const index = parseInt(speaker.replace(/\D/g, '')) || 0
    return types[index % types.length]
}

const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const drawWaveform = () => {
    if (!waveformCanvas.value) return
    
    const canvas = waveformCanvas.value
    const ctx = canvas.getContext('2d')
    const width = canvas.width = canvas.offsetWidth
    const height = canvas.height = 200
    
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)
    
    const barCount = 200
    const barWidth = width / barCount
    const centerY = height / 2
    
    ctx.beginPath()
    for (let i = 0; i < barCount; i++) {
        const barHeight = Math.random() * height * 0.8
        const x = i * barWidth
        const y1 = centerY - barHeight / 2
        const y2 = centerY + barHeight / 2
        
        ctx.moveTo(x, y1)
        ctx.lineTo(x, y2)
    }
    ctx.strokeStyle = 'rgba(233, 69, 96, 0.8)'
    ctx.lineWidth = 1
    ctx.stroke()
    
    ctx.strokeStyle = 'rgba(136, 146, 176, 0.3)'
    ctx.beginPath()
    ctx.moveTo(0, centerY)
    ctx.lineTo(width, centerY)
    ctx.stroke()
}

const drawSpectrum = () => {
    if (!spectrumCanvas.value) return
    
    const canvas = spectrumCanvas.value
    const ctx = canvas.getContext('2d')
    const width = canvas.width = canvas.offsetWidth
    const height = canvas.height = 200
    
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)
    
    const barCount = 128
    const barWidth = width / barCount
    
    for (let i = 0; i < barCount; i++) {
        const barHeight = Math.random() * height * 0.9 + 10
        const x = i * barWidth
        const y = height - barHeight
        
        const gradient = ctx.createLinearGradient(x, height, x, y)
        gradient.addColorStop(0, 'rgba(233, 69, 96, 0.3)')
        gradient.addColorStop(1, 'rgba(233, 69, 96, 0.9)')
        
        ctx.fillStyle = gradient
        ctx.fillRect(x, y, barWidth - 1, barHeight)
    }
}

const downloadResult = async (type) => {
    if (!currentTask.value) return
    
    try {
        window.open(`/api/download/${currentTask.value.task_id}?file_type=${type}`, '_blank')
        ElMessage.success('开始下载')
    } catch (e) {
        ElMessage.error('下载失败')
    }
}

const refreshTasks = async () => {
    try {
        const response = await axios.get('/api/tasks')
        taskList.value = response.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    } catch (e) {
        console.error('Failed to fetch tasks:', e)
    }
}

const viewTask = (task) => {
    currentTask.value = task
    if (task.result) {
        nextTick(() => {
            drawWaveform()
            drawSpectrum()
        })
    }
}

onMounted(() => {
    refreshTasks()
})

onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.processing-container {
    max-width: 1600px;
    margin: 0 auto;
}

.header-card,
.upload-card,
.pipeline-card,
.progress-card,
.tasks-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    margin-bottom: 20px;
}

.header-content h2 {
    color: #ffffff;
    margin: 0;
}

.subtitle {
    color: #8892b0;
    font-size: 14px;
    margin: 5px 0 0 0;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: #e94560;
}

.upload-icon {
    font-size: 64px;
    color: #8892b0;
}

:deep(.el-upload-dragger) {
    background: rgba(10, 10, 15, 0.5) !important;
    border: 2px dashed #0f3460 !important;
}

:deep(.el-upload-dragger:hover) {
    border-color: #e94560 !important;
}

.processing-options h4 {
    color: #ffffff;
    margin-bottom: 15px;
}

:deep(.el-form-item__label) {
    color: #8892b0 !important;
}

.pipeline-steps {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    border-radius: 8px;
    background: rgba(10, 10, 15, 0.3);
    transition: all 0.3s;
}

.pipeline-step.done {
    background: rgba(103, 194, 58, 0.1);
    border: 1px solid rgba(103, 194, 58, 0.3);
}

.pipeline-step.active {
    background: rgba(233, 69, 96, 0.1);
    border: 1px solid rgba(233, 69, 96, 0.3);
}

.step-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #0f3460;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    color: #8892b0;
    font-weight: bold;
}

.pipeline-step.done .step-icon {
    background: #67c23a;
    color: white;
}

.pipeline-step.active .step-icon {
    background: #e94560;
    color: white;
}

.loading {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.step-name {
    color: #ffffff;
    font-weight: 500;
    font-size: 14px;
}

.step-desc {
    color: #8892b0;
    font-size: 12px;
    margin-top: 2px;
}

.no-task {
    padding: 40px 0;
}

.main-progress {
    margin-bottom: 15px;
}

.progress-message {
    color: #8892b0;
    text-align: center;
    margin-bottom: 20px;
}

:deep(.el-tabs__item) {
    color: #8892b0;
}

:deep(.el-tabs__item.is-active) {
    color: #e94560;
}

:deep(.el-tabs__active-bar) {
    background: #e94560;
}

.waveform-container,
.spectrum-container {
    background: #0a0a0f;
    border-radius: 8px;
    padding: 20px;
}

.waveform-canvas,
.spectrum-canvas {
    width: 100%;
    display: block;
}

.transcript-content {
    max-height: 400px;
    overflow-y: auto;
}

.transcript-text h4 {
    color: #ffffff;
    margin: 15px 0 10px 0;
}

.transcript-text p {
    color: #e0e0e0;
    line-height: 1.8;
    padding: 15px;
    background: rgba(10, 10, 15, 0.5);
    border-radius: 8px;
}

.speaker-segments {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.segment-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
    background: rgba(10, 10, 15, 0.3);
    border-radius: 8px;
}

.segment-time {
    color: #8892b0;
    font-size: 12px;
    font-family: monospace;
    white-space: nowrap;
}

.segment-text {
    color: #e0e0e0;
    flex: 1;
}

.no-result {
    color: #8892b0;
    text-align: center;
    padding: 40px;
}

.summary-content h4 {
    color: #ffffff;
    margin: 15px 0 10px 0;
}

.summary-content ul {
    color: #e0e0e0;
    padding-left: 20px;
    line-height: 2;
}

.summary-content p {
    color: #e0e0e0;
    line-height: 1.8;
}

.topic-tag {
    margin: 5px;
}

.download-section h4 {
    color: #ffffff;
    margin-bottom: 15px;
}

.download-buttons {
    display: flex;
    gap: 15px;
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

:deep(.el-table) {
    --el-table-bg-color: transparent;
    --el-table-tr-bg-color: transparent;
    --el-table-text-color: #e0e0e0;
    --el-table-header-text-color: #8892b0;
    --el-table-border-color: #0f3460;
}

:deep(.el-table th) {
    background: rgba(10, 10, 15, 0.5) !important;
}

:deep(.el-table tr:hover > td) {
    background: rgba(233, 69, 96, 0.05) !important;
}
</style>
