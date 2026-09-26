<template>
    <div class="transcripts-container">
        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="header-card">
                    <div class="header-content">
                        <div>
                            <h2>会议纪要管理</h2>
                            <p class="subtitle">Meeting Minutes Management - 查看与管理生成的会议纪要</p>
                        </div>
                        <div class="header-actions">
                            <el-button type="primary" @click="loadTranscripts">
                                <el-icon><Refresh /></el-icon>
                                刷新列表
                            </el-button>
                            <el-button type="warning" @click="showDecryptDialog = true">
                                <el-icon><Key /></el-icon>
                                解密文件
                            </el-button>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="6">
                <el-card class="list-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Document /></el-icon>
                            <span>纪要列表</span>
                        </div>
                    </template>
                    <el-input 
                        v-model="searchKeyword" 
                        placeholder="搜索会议纪要..." 
                        :prefix-icon="Search"
                        clearable
                        class="search-input"
                    />
                    <el-divider />
                    <div class="transcript-list">
                        <div 
                            v-for="transcript in filteredTranscripts" 
                            :key="transcript.task_id"
                            class="transcript-item"
                            :class="{ active: selectedTranscript?.task_id === transcript.task_id }"
                            @click="selectTranscript(transcript)"
                        >
                            <div class="transcript-title">
                                {{ transcript.title || '未命名会议' }}
                            </div>
                            <div class="transcript-meta">
                                <span class="meta-item">
                                    <el-icon><Calendar /></el-icon>
                                    {{ formatDate(transcript.created_at) }}
                                </span>
                                <span class="meta-item">
                                    <el-icon><User /></el-icon>
                                    {{ transcript.speakers?.length || 0 }} 人
                                </span>
                            </div>
                            <el-tag 
                                :type="transcript.has_summary ? 'success' : 'info'" 
                                size="small"
                                class="transcript-tag"
                            >
                                {{ transcript.has_summary ? '已生成摘要' : '仅转写' }}
                            </el-tag>
                        </div>
                        <div v-if="filteredTranscripts.length === 0" class="empty-list">
                            <el-empty description="暂无会议纪要" :image-size="80" />
                        </div>
                    </div>
                </el-card>
            </el-col>

            <el-col :span="18">
                <el-card class="viewer-card" v-if="selectedTranscript">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Reading /></el-icon>
                            <span>{{ selectedTranscript.title || '会议纪要' }}</span>
                            <div class="header-actions">
                                <el-button size="small" @click="exportMarkdown">
                                    <el-icon><Download /></el-icon>
                                    导出 MD
                                </el-button>
                                <el-button size="small" type="success" @click="exportPDF">
                                    <el-icon><Printer /></el-icon>
                                    打印
                                </el-button>
                                <el-button size="small" type="warning" @click="sendEmail">
                                    <el-icon><Message /></el-icon>
                                    发送邮件
                                </el-button>
                            </div>
                        </div>
                    </template>

                    <div class="transcript-viewer">
                        <div class="viewer-header">
                            <h1>{{ selectedTranscript.summary?.summary?.title || '会议纪要' }}</h1>
                            <div class="viewer-meta">
                                <span>日期: {{ selectedTranscript.summary?.summary?.date || selectedTranscript.created_at }}</span>
                                <span>参会人员: {{ selectedTranscript.summary?.summary?.participants?.join(', ') || selectedTranscript.speakers?.join(', ') || '未知' }}</span>
                            </div>
                        </div>

                        <el-alert 
                            title="内容声明" 
                            type="warning" 
                            :closable="false"
                            class="content-notice"
                            show-icon
                        >
                            本纪要基于激光测振仪获取的音频生成，内容可能存在不准确性，仅供参考。
                        </el-alert>

                        <div class="viewer-tabs">
                            <el-tabs v-model="activeTab">
                                <el-tab-pane label="AI摘要" name="summary" v-if="selectedTranscript.summary">
                                    <div class="summary-section">
                                        <h3>会议概述</h3>
                                        <p class="summary-text">{{ selectedTranscript.summary.summary?.summary }}</p>
                                        
                                        <el-divider />
                                        
                                        <div class="summary-grid">
                                            <div class="summary-block">
                                                <h4><el-icon><List /></el-icon> 讨论议题</h4>
                                                <ul>
                                                    <li v-for="(topic, index) in selectedTranscript.summary.summary?.key_topics" :key="index">
                                                        {{ topic }}
                                                    </li>
                                                </ul>
                                            </div>
                                            <div class="summary-block">
                                                <h4><el-icon><Check /></el-icon> 重要决定</h4>
                                                <ul>
                                                    <li v-for="(decision, index) in selectedTranscript.summary.summary?.decisions" :key="index">
                                                        {{ decision }}
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                        
                                        <el-divider />
                                        
                                        <h3><el-icon><Warning /></el-icon> 风险与问题</h3>
                                        <el-table :data="selectedTranscript.summary.summary?.risks?.map(r => ({risk: r})) || []" border>
                                            <el-table-column prop="risk" label="风险描述" />
                                        </el-table>
                                        
                                        <el-divider />
                                        
                                        <h3><el-icon><Calendar /></el-icon> 行动项</h3>
                                        <el-table :data="selectedTranscript.summary.summary?.action_items || []" border>
                                            <el-table-column prop="task" label="任务" />
                                            <el-table-column prop="assignee" label="负责人" width="120" />
                                            <el-table-column prop="deadline" label="截止日期" width="140" />
                                        </el-table>
                                        
                                        <el-divider v-if="selectedTranscript.summary.summary?.next_meeting" />
                                        
                                        <div v-if="selectedTranscript.summary.summary?.next_meeting" class="next-meeting">
                                            <el-tag type="primary" size="large">
                                                <el-icon><Clock /></el-icon>
                                                下次会议: {{ selectedTranscript.summary.summary.next_meeting }}
                                            </el-tag>
                                        </div>
                                    </div>
                                </el-tab-pane>
                                
                                <el-tab-pane label="完整转写" name="transcript">
                                    <div class="full-transcript">
                                        <div 
                                            v-for="(segment, index) in selectedTranscript.transcript?.segments" 
                                            :key="index"
                                            class="transcript-segment"
                                        >
                                            <div class="segment-header">
                                                <el-tag :type="getSpeakerTagType(segment.speaker)" size="large">
                                                    {{ segment.speaker }}
                                                </el-tag>
                                                <span class="segment-timestamp">
                                                    {{ formatTime(segment.start) }} - {{ formatTime(segment.end) }}
                                                </span>
                                            </div>
                                            <p class="segment-content">{{ segment.text }}</p>
                                        </div>
                                    </div>
                                </el-tab-pane>
                                
                                <el-tab-pane label="发言统计" name="stats">
                                    <div class="stats-section">
                                        <el-row :gutter="20">
                                            <el-col :span="12">
                                                <el-card class="stat-card">
                                                    <template #header>
                                                        <span>发言时长统计</span>
                                                    </template>
                                                    <div class="chart-container">
                                                        <canvas ref="durationChart"></canvas>
                                                    </div>
                                                </el-card>
                                            </el-col>
                                            <el-col :span="12">
                                                <el-card class="stat-card">
                                                    <template #header>
                                                        <span>发言次数统计</span>
                                                    </template>
                                                    <div class="chart-container">
                                                        <canvas ref="countChart"></canvas>
                                                    </div>
                                                </el-card>
                                            </el-col>
                                        </el-row>
                                        
                                        <el-divider />
                                        
                                        <el-table 
                                            :data="getSpeakerStats()" 
                                            border
                                            style="width: 100%; margin-top: 20px"
                                        >
                                            <el-table-column prop="speaker" label="发言者" width="150">
                                                <template #default="scope">
                                                    <el-tag :type="getSpeakerTagType(scope.row.speaker)">
                                                        {{ scope.row.speaker }}
                                                    </el-tag>
                                                </template>
                                            </el-table-column>
                                            <el-table-column prop="total_time" label="总时长(秒)" width="120">
                                                <template #default="scope">
                                                    {{ scope.row.total_time.toFixed(1) }}s
                                                </template>
                                            </el-table-column>
                                            <el-table-column prop="segments" label="发言次数" width="120" />
                                            <el-table-column prop="avg_length" label="平均时长(秒)" width="120">
                                                <template #default="scope">
                                                    {{ scope.row.avg_length.toFixed(1) }}s
                                                </template>
                                            </el-table-column>
                                            <el-table-column prop="words" label="字数" />
                                        </el-table>
                                    </div>
                                </el-tab-pane>
                                
                                <el-tab-pane label="原始数据" name="raw">
                                    <div class="raw-data">
                                        <el-alert 
                                            title="原始JSON数据" 
                                            type="info" 
                                            :closable="false"
                                            show-icon
                                        >
                                            以下是系统生成的原始数据，包含所有处理细节。
                                        </el-alert>
                                        <pre class="json-preview">{{ JSON.stringify(selectedTranscript, null, 2) }}</pre>
                                    </div>
                                </el-tab-pane>
                            </el-tabs>
                        </div>
                    </div>
                </el-card>
                
                <el-card class="viewer-card empty-viewer" v-else>
                    <el-empty description="请从左侧选择一个会议纪要查看" :image-size="120" />
                </el-card>
            </el-col>
        </el-row>

        <el-dialog 
            v-model="showDecryptDialog" 
            title="解密会议纪要文件"
            width="500px"
        >
            <el-form :model="decryptForm" label-width="100px">
                <el-form-item label="加密文件">
                    <el-upload
                        :auto-upload="false"
                        :show-file-list="false"
                        @change="handleEncryptedFile"
                    >
                        <el-button>选择文件</el-button>
                        <span v-if="decryptForm.file" class="file-name">{{ decryptForm.file.name }}</span>
                    </el-upload>
                </el-form-item>
                <el-form-item label="解密密钥">
                    <el-input 
                        v-model="decryptForm.key" 
                        type="password" 
                        placeholder="输入32位加密密钥"
                        show-password
                    />
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showDecryptDialog = false">取消</el-button>
                <el-button type="primary" @click="decryptFile" :loading="decrypting">解密</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import {
    Refresh,
    Key,
    Document,
    Search,
    Calendar,
    User,
    Reading,
    Download,
    Printer,
    Message,
    List,
    Check,
    Warning,
    Clock
} from '@element-plus/icons-vue'

const transcripts = ref([])
const selectedTranscript = ref(null)
const searchKeyword = ref('')
const activeTab = ref('summary')
const showDecryptDialog = ref(false)
const decrypting = ref(false)
const durationChart = ref(null)
const countChart = ref(null)

const decryptForm = ref({
    file: null,
    key: ''
})

const filteredTranscripts = computed(() => {
    if (!searchKeyword.value) return transcripts.value
    const keyword = searchKeyword.value.toLowerCase()
    return transcripts.value.filter(t => 
        (t.title || '').toLowerCase().includes(keyword) ||
        JSON.stringify(t).toLowerCase().includes(keyword)
    )
})

const loadTranscripts = async () => {
    try {
        const response = await axios.get('/api/tasks')
        transcripts.value = response.data
            .filter(t => t.status === 'completed' && t.result)
            .map(t => ({
                task_id: t.task_id,
                created_at: t.created_at,
                title: t.result?.summary?.summary?.title || '会议纪要',
                speakers: t.result?.transcript?.speakers || [],
                has_summary: !!t.result?.summary,
                transcript: t.result?.transcript,
                summary: t.result?.summary,
                markdown_summary: t.result?.markdown_summary,
                markdown_transcript: t.result?.markdown_transcript
            }))
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    } catch (e) {
        console.error('Failed to load transcripts:', e)
    }
}

const selectTranscript = (transcript) => {
    selectedTranscript.value = transcript
    activeTab.value = transcript.has_summary ? 'summary' : 'transcript'
    
    nextTick(() => {
        if (transcript.transcript?.speaker_stats) {
            drawCharts()
        }
    })
}

const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const getSpeakerTagType = (speaker) => {
    const types = ['primary', 'success', 'warning', 'info', 'danger']
    const index = parseInt(speaker?.replace(/\D/g, '')) || 0
    return types[index % types.length]
}

const getSpeakerStats = () => {
    if (!selectedTranscript.value?.transcript?.speaker_stats) return []
    return Object.entries(selectedTranscript.value.transcript.speaker_stats).map(([speaker, stats]) => ({
        speaker,
        ...stats
    }))
}

const drawCharts = async () => {
    const stats = getSpeakerStats()
    if (stats.length === 0) return
    
    await nextTick()
    
    const Chart = (await import('chart.js/auto')).default
    
    if (durationChart.value) {
        const ctx = durationChart.value.getContext('2d')
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: stats.map(s => s.speaker),
                datasets: [{
                    data: stats.map(s => s.total_time),
                    backgroundColor: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: { color: '#e0e0e0' }
                    }
                }
            }
        })
    }
    
    if (countChart.value) {
        const ctx = countChart.value.getContext('2d')
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: stats.map(s => s.speaker),
                datasets: [{
                    label: '发言次数',
                    data: stats.map(s => s.segments),
                    backgroundColor: 'rgba(233, 69, 96, 0.7)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: { color: '#e0e0e0' }
                    }
                },
                scales: {
                    y: {
                        ticks: { color: '#8892b0' },
                        grid: { color: 'rgba(136, 146, 176, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#8892b0' },
                        grid: { color: 'rgba(136, 146, 176, 0.1)' }
                    }
                }
            }
        })
    }
}

const exportMarkdown = () => {
    if (!selectedTranscript.value) return
    const content = selectedTranscript.value.markdown_summary || selectedTranscript.value.markdown_transcript
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `meeting_minutes_${selectedTranscript.value.task_id}.md`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
}

const exportPDF = () => {
    window.print()
}

const sendEmail = () => {
    ElMessage.info('邮件发送功能请在处理页面配置')
}

const handleEncryptedFile = (file) => {
    decryptForm.value.file = file
}

const decryptFile = async () => {
    if (!decryptForm.value.file || !decryptForm.value.key) {
        ElMessage.warning('请选择文件并输入密钥')
        return
    }
    
    decrypting.value = true
    
    try {
        const formData = new FormData()
        formData.append('file', decryptForm.value.file.raw)
        formData.append('key', decryptForm.value.key)
        
        const response = await axios.post('/api/decrypt', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        if (response.data.success) {
            ElMessage.success('解密成功')
            const blob = new Blob([response.data.content], { type: 'text/markdown' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'decrypted_meeting_minutes.md'
            a.click()
            URL.revokeObjectURL(url)
            showDecryptDialog.value = false
        } else {
            ElMessage.error('解密失败: ' + response.data.error)
        }
    } catch (e) {
        ElMessage.error('解密失败: ' + (e.response?.data?.detail || e.message))
    } finally {
        decrypting.value = false
    }
}

watch(activeTab, (newVal) => {
    if (newVal === 'stats' && selectedTranscript.value) {
        nextTick(() => drawCharts())
    }
})

onMounted(() => {
    loadTranscripts()
})
</script>

<style scoped>
.transcripts-container {
    max-width: 1600px;
    margin: 0 auto;
}

.header-card,
.list-card,
.viewer-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    margin-bottom: 20px;
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

.header-actions {
    display: flex;
    gap: 10px;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: #e94560;
}

.search-input {
    margin-bottom: 10px;
}

.transcript-list {
    max-height: 70vh;
    overflow-y: auto;
}

.transcript-item {
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
    background: rgba(10, 10, 15, 0.3);
    cursor: pointer;
    transition: all 0.3s;
    border: 1px solid transparent;
}

.transcript-item:hover {
    background: rgba(233, 69, 96, 0.1);
    border-color: rgba(233, 69, 96, 0.3);
}

.transcript-item.active {
    background: rgba(233, 69, 96, 0.15);
    border-color: #e94560;
}

.transcript-title {
    color: #ffffff;
    font-weight: 500;
    margin-bottom: 8px;
}

.transcript-meta {
    display: flex;
    gap: 15px;
    margin-bottom: 8px;
}

.meta-item {
    color: #8892b0;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 4px;
}

.transcript-tag {
    margin-top: 5px;
}

.empty-list {
    padding: 40px 0;
}

.viewer-card .card-header {
    justify-content: space-between;
}

.transcript-viewer {
    max-height: 80vh;
    overflow-y: auto;
}

.viewer-header {
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #0f3460;
}

.viewer-header h1 {
    color: #ffffff;
    margin-bottom: 10px;
}

.viewer-meta {
    color: #8892b0;
    display: flex;
    justify-content: center;
    gap: 30px;
}

.content-notice {
    margin-bottom: 20px;
}

.empty-viewer {
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.summary-section h3 {
    color: #e94560;
    margin: 20px 0 15px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.summary-text {
    color: #e0e0e0;
    line-height: 2;
    padding: 15px;
    background: rgba(10, 10, 15, 0.3);
    border-radius: 8px;
}

.summary-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.summary-block h4 {
    color: #ffffff;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.summary-block ul {
    color: #e0e0e0;
    padding-left: 20px;
    line-height: 2;
}

.next-meeting {
    text-align: center;
    padding: 20px;
}

.full-transcript {
    padding: 10px 0;
}

.transcript-segment {
    margin-bottom: 20px;
    padding: 15px;
    background: rgba(10, 10, 15, 0.3);
    border-radius: 8px;
    border-left: 3px solid #e94560;
}

.segment-header {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 10px;
}

.segment-timestamp {
    color: #8892b0;
    font-size: 12px;
    font-family: monospace;
}

.segment-content {
    color: #e0e0e0;
    line-height: 1.8;
    margin: 0;
}

.stats-section {
    padding: 20px 0;
}

.stat-card {
    background: rgba(10, 10, 15, 0.3) !important;
    border: 1px solid #0f3460 !important;
}

.chart-container {
    height: 250px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.chart-container canvas {
    max-height: 100%;
}

.raw-data {
    padding: 20px 0;
}

.json-preview {
    background: #0a0a0f;
    padding: 20px;
    border-radius: 8px;
    overflow-x: auto;
    max-height: 500px;
    color: #67c23a;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    margin-top: 15px;
}

.file-name {
    margin-left: 10px;
    color: #8892b0;
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

:deep(.el-form-item__label) {
    color: #8892b0 !important;
}

@media print {
    .header-card,
    .list-card,
    .viewer-card .card-header {
        display: none;
    }
    
    .viewer-card {
        border: none;
        background: white;
    }
    
    .transcript-viewer {
        max-height: none;
        overflow: visible;
    }
}
</style>
