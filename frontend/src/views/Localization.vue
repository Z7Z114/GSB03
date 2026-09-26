<template>
    <div class="localization-container">
        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="header-card">
                    <div class="header-content">
                        <div>
                            <h2>声源定位系统</h2>
                            <p class="subtitle">Sound Source Localization System</p>
                        </div>
                        <div class="header-actions">
                            <el-button 
                                :type="isConnected ? 'success' : 'danger'"
                                :icon="isConnected ? Connection : Close"
                                @click="toggleConnection"
                            >
                                {{ isConnected ? '已连接' : '未连接' }}
                            </el-button>
                            <el-button 
                                type="primary" 
                                :icon="isScanning ? VideoPause : VideoPlay"
                                @click="toggleScanning"
                                :disabled="!isConnected"
                            >
                                {{ isScanning ? '停止扫描' : '开始扫描' }}
                            </el-button>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="main-row">
            <el-col :span="16">
                <el-card class="visualization-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Location /></el-icon>
                            <span>声源定位热力图</span>
                            <el-tag type="info" v-if="latestPosition">
                                位置: ({{ latestPosition.x.toFixed(2) }}, {{ latestPosition.y.toFixed(2) }})
                            </el-tag>
                        </div>
                    </template>
                    <div class="visualization-wrapper">
                        <canvas ref="heatmapCanvas" class="heatmap-canvas"></canvas>
                        <div class="source-markers" v-if="detectedSources.length > 0">
                            <div 
                                v-for="(source, index) in detectedSources" 
                                :key="index"
                                class="source-marker"
                                :style="getMarkerStyle(source)"
                            >
                                <div class="marker-pulse" :style="{ animationDelay: `${index * 0.3}s` }"></div>
                                <div class="marker-dot"></div>
                                <div class="marker-label">{{ index + 1 }}</div>
                            </div>
                        </div>
                        <div class="microphone-array">
                            <div 
                                v-for="(mic, index) in microphonePositions" 
                                :key="index"
                                class="microphone"
                                :style="getMicStyle(mic)"
                            >
                                <el-icon><Mic /></el-icon>
                            </div>
                        </div>
                    </div>
                    <div class="visualization-info">
                        <span>扫描范围: ±{{ scanRange }}m</span>
                        <span>分辨率: {{ resolution }}x{{ resolution }}</span>
                        <span>检测到声源: {{ detectedSources.length }}</span>
                    </div>
                </el-card>
            </el-col>

            <el-col :span="8">
                <el-card class="info-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><DataAnalysis /></el-icon>
                            <span>实时数据</span>
                        </div>
                    </template>
                    
                    <div class="status-section">
                        <h4>系统状态</h4>
                        <el-descriptions :column="1" border size="small">
                            <el-descriptions-item label="连接状态">
                                <el-tag :type="isConnected ? 'success' : 'danger'">
                                    {{ isConnected ? '已连接' : '未连接' }}
                                </el-tag>
                            </el-descriptions-item>
                            <el-descriptions-item label="扫描状态">
                                <el-tag :type="isScanning ? 'primary' : 'info'">
                                    {{ isScanning ? '扫描中' : '已停止' }}
                                </el-tag>
                            </el-descriptions-item>
                            <el-descriptions-item label="置信度">
                                <el-progress 
                                    :percentage="Math.round(confidence * 100)" 
                                    :color="getConfidenceColor(confidence)"
                                    :stroke-width="8"
                                />
                            </el-descriptions-item>
                        </el-descriptions>
                    </div>

                    <el-divider />

                    <div class="sources-section">
                        <h4>检测到的声源</h4>
                        <div v-if="detectedSources.length === 0" class="empty-state">
                            <el-empty description="暂未检测到声源" :image-size="80" />
                        </div>
                        <div v-else class="sources-list">
                            <div 
                                v-for="(source, index) in detectedSources" 
                                :key="index"
                                class="source-item"
                            >
                                <div class="source-index">{{ index + 1 }}</div>
                                <div class="source-info">
                                    <div class="source-coords">
                                        ({{ source.x.toFixed(2) }}m, {{ source.y.toFixed(2) }}m)
                                    </div>
                                    <el-progress 
                                        :percentage="Math.round(source.confidence * 100)" 
                                        :color="getConfidenceColor(source.confidence)"
                                        :stroke-width="6"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <el-divider />

                    <div class="history-section">
                        <h4>位置历史</h4>
                        <div class="position-log" ref="positionLog">
                            <div v-for="(log, index) in positionHistory.slice(-10)" :key="index" class="log-item">
                                <span class="log-time">{{ log.time }}</span>
                                <span class="log-pos">{{ log.position }}</span>
                            </div>
                            <div v-if="positionHistory.length === 0" class="empty-history">
                                暂无历史记录
                            </div>
                        </div>
                    </div>
                </el-card>

                <el-card class="upload-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Upload /></el-icon>
                            <span>离线定位分析</span>
                        </div>
                    </template>
                    <el-upload
                        multiple
                        action="/api/process/localization"
                        :auto-upload="false"
                        :file-list="uploadedFiles"
                        @change="handleFileChange"
                        drag
                    >
                        <el-icon class="upload-icon"><UploadFilled /></el-icon>
                        <div class="el-upload__text">拖放文件到此处，或<em>点击上传</em></div>
                        <template #tip>
                            <div class="el-upload__tip">
                                至少上传2个麦克风音频文件 (WAV格式)
                            </div>
                        </template>
                    </el-upload>
                    <el-button 
                        type="primary" 
                        style="width: 100%; margin-top: 15px"
                        :disabled="uploadedFiles.length < 2"
                        @click="processOfflineLocalization"
                        :loading="processingOffline"
                    >
                        开始定位分析
                    </el-button>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="control-card">
                    <template #header>
                        <div class="card-header">
                            <el-icon><Setting /></el-icon>
                            <span>参数设置</span>
                        </div>
                    </template>
                    <el-form :inline="true" :model="settings">
                        <el-form-item label="扫描范围 (m)">
                            <el-slider v-model="settings.scanRange" :min="1" :max="20" :step="0.5" style="width: 200px" />
                        </el-form-item>
                        <el-form-item label="分辨率">
                            <el-slider v-model="settings.resolution" :min="20" :max="100" :step="10" style="width: 200px" />
                        </el-form-item>
                        <el-form-item label="平滑因子">
                            <el-slider v-model="settings.smoothing" :min="0" :max="1" :step="0.1" style="width: 200px" />
                        </el-form-item>
                        <el-form-item label="置信度阈值">
                            <el-slider v-model="settings.confidenceThreshold" :min="0.3" :max="0.9" :step="0.05" style="width: 200px" />
                        </el-form-item>
                    </el-form>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import {
    Connection,
    Close,
    VideoPlay,
    VideoPause,
    Location,
    DataAnalysis,
    Upload,
    UploadFilled,
    Setting,
    Mic
} from '@element-plus/icons-vue'

const isConnected = ref(false)
const isScanning = ref(false)
const confidence = ref(0)
const scanRange = ref(5)
const resolution = ref(50)
const uploadedFiles = ref([])
const processingOffline = ref(false)
const heatmapCanvas = ref(null)
const positionLog = ref(null)

const microphonePositions = [
    { x: -0.05, y: -0.02 },
    { x: 0.05, y: -0.02 },
    { x: 0, y: 0.067 },
    { x: 0, y: 0.01 }
]

const detectedSources = ref([])
const positionHistory = ref([])
const latestPosition = ref(null)

const settings = ref({
    scanRange: 5,
    resolution: 50,
    smoothing: 0.7,
    confidenceThreshold: 0.6
})

let ws = null
let canvasContext = null
let animationId = null
let heatmapData = null

const getConfidenceColor = (conf) => {
    if (conf >= 0.8) return '#67c23a'
    if (conf >= 0.6) return '#e6a23c'
    return '#f56c6c'
}

const getMarkerStyle = (source) => {
    const canvasWidth = 600
    const canvasHeight = 600
    const range = scanRange.value
    const x = ((source.x + range) / (2 * range)) * canvasWidth
    const y = ((-source.y + range) / (2 * range)) * canvasHeight
    return {
        left: `${x}px`,
        top: `${y}px`,
        opacity: source.confidence
    }
}

const getMicStyle = (mic) => {
    const canvasWidth = 600
    const canvasHeight = 600
    const range = scanRange.value
    const x = ((mic.x + range) / (2 * range)) * canvasWidth
    const y = ((-mic.y + range) / (2 * range)) * canvasHeight
    return {
        left: `${x}px`,
        top: `${y}px`
    }
}

const toggleConnection = () => {
    if (isConnected.value) {
        disconnectWebSocket()
    } else {
        connectWebSocket()
    }
}

const connectWebSocket = () => {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/realtime`)
        
        ws.onopen = () => {
            isConnected.value = true
            ElMessage.success('WebSocket连接成功')
        }
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            handleWebSocketMessage(data)
        }
        
        ws.onclose = () => {
            isConnected.value = false
            isScanning.value = false
            ElMessage.warning('WebSocket连接已断开')
        }
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            ElMessage.error('WebSocket连接错误')
        }
    } catch (e) {
        ElMessage.error('连接失败')
    }
}

const disconnectWebSocket = () => {
    if (ws) {
        ws.close()
        ws = null
    }
    isConnected.value = false
    isScanning.value = false
}

const handleWebSocketMessage = (data) => {
    if (data.type === 'localization_update') {
        const pos = data.position
        latestPosition.value = { x: pos[0], y: pos[1] }
        confidence.value = data.confidence
        
        if (data.confidence > settings.value.confidenceThreshold) {
            const now = new Date()
            positionHistory.value.push({
                time: now.toLocaleTimeString(),
                position: `(${pos[0].toFixed(2)}, ${pos[1].toFixed(2)})`,
                x: pos[0],
                y: pos[1],
                confidence: data.confidence
            })
            
            updateHeatmap(pos[0], pos[1], data.confidence)
            
            if (positionLog.value) {
                positionLog.value.scrollTop = positionLog.value.scrollHeight
            }
        }
    }
}

const toggleScanning = () => {
    if (!isConnected.value) {
        ElMessage.warning('请先连接WebSocket')
        return
    }
    isScanning.value = !isScanning.value
    
    if (isScanning.value) {
        startSimulation()
    } else {
        stopSimulation()
    }
}

const startSimulation = () => {
    const simulateData = () => {
        if (!isScanning.value) return
        
        const angle = Math.random() * Math.PI * 2
        const distance = Math.random() * (scanRange.value * 0.8)
        const x = Math.cos(angle) * distance
        const y = Math.sin(angle) * distance
        const conf = 0.5 + Math.random() * 0.5
        
        handleWebSocketMessage({
            type: 'localization_update',
            position: [x, y, 0],
            confidence: conf,
            timestamp: new Date().toISOString()
        })
        
        if (Math.random() > 0.7) {
            const newSource = {
                x: x + (Math.random() - 0.5) * 2,
                y: y + (Math.random() - 0.5) * 2,
                confidence: conf
            }
            if (detectedSources.value.length < 5) {
                detectedSources.value.push(newSource)
            } else {
                const minIndex = detectedSources.value.findIndex(s => s.confidence === Math.min(...detectedSources.value.map(s => s.confidence)))
                if (newSource.confidence > detectedSources.value[minIndex].confidence) {
                    detectedSources.value[minIndex] = newSource
                }
            }
        }
        
        animationId = setTimeout(simulateData, 1000)
    }
    
    simulateData()
}

const stopSimulation = () => {
    if (animationId) {
        clearTimeout(animationId)
        animationId = null
    }
}

const initCanvas = async () => {
    await nextTick()
    if (heatmapCanvas.value) {
        const canvas = heatmapCanvas.value
        canvas.width = 600
        canvas.height = 600
        canvasContext = canvas.getContext('2d')
        drawGrid()
        heatmapData = Array(resolution.value).fill().map(() => Array(resolution.value).fill(0))
    }
}

const drawGrid = () => {
    if (!canvasContext) return
    
    const ctx = canvasContext
    const width = 600
    const height = 600
    const range = scanRange.value
    
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)
    
    ctx.strokeStyle = '#1a1a2e'
    ctx.lineWidth = 1
    
    const gridStep = width / (range * 2)
    for (let i = 0; i <= range * 2; i++) {
        ctx.beginPath()
        ctx.moveTo(i * gridStep, 0)
        ctx.lineTo(i * gridStep, height)
        ctx.stroke()
        
        ctx.beginPath()
        ctx.moveTo(0, i * gridStep)
        ctx.lineTo(width, i * gridStep)
        ctx.stroke()
    }
    
    ctx.strokeStyle = '#e94560'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(width / 2, 0)
    ctx.lineTo(width / 2, height)
    ctx.stroke()
    
    ctx.beginPath()
    ctx.moveTo(0, height / 2)
    ctx.lineTo(width, height / 2)
    ctx.stroke()
    
    ctx.fillStyle = '#8892b0'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    for (let i = -range; i <= range; i++) {
        const x = ((i + range) / (range * 2)) * width
        ctx.fillText(`${i}m`, x, height - 10)
        ctx.fillText(`${-i}m`, 10, ((i + range) / (range * 2)) * height)
    }
}

const updateHeatmap = (x, y, conf) => {
    if (!canvasContext || !heatmapData) return
    
    const width = 600
    const height = 600
    const range = scanRange.value
    
    drawGrid()
    
    const gridX = Math.floor(((x + range) / (range * 2)) * resolution.value)
    const gridY = Math.floor(((-y + range) / (range * 2)) * resolution.value)
    
    for (let i = 0; i < resolution.value; i++) {
        for (let j = 0; j < resolution.value; j++) {
            const dx = i - gridX
            const dy = j - gridY
            const dist = Math.sqrt(dx * dx + dy * dy)
            const influence = Math.exp(-dist / (resolution.value * 0.1)) * conf
            heatmapData[i][j] = Math.max(heatmapData[i][j] * settings.value.smoothing, influence)
        }
    }
    
    const cellWidth = width / resolution.value
    const cellHeight = height / resolution.value
    
    for (let i = 0; i < resolution.value; i++) {
        for (let j = 0; j < resolution.value; j++) {
            const value = heatmapData[i][j]
            if (value > 0.1) {
                const r = Math.floor(233 * value)
                const g = Math.floor(69 * value)
                const b = Math.floor(96 * value)
                canvasContext.fillStyle = `rgba(${r}, ${g}, ${b}, ${value * 0.6})`
                canvasContext.fillRect(i * cellWidth, j * cellHeight, cellWidth + 1, cellHeight + 1)
            }
        }
    }
}

const handleFileChange = (file, fileList) => {
    uploadedFiles.value = fileList
}

const processOfflineLocalization = async () => {
    if (uploadedFiles.value.length < 2) {
        ElMessage.warning('请至少上传2个音频文件')
        return
    }
    
    processingOffline.value = true
    
    try {
        const formData = new FormData()
        uploadedFiles.value.forEach(file => {
            formData.append('files', file.raw)
        })
        
        const response = await axios.post('/api/process/localization', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        if (response.data.success) {
            const loc = response.data.localization
            detectedSources.value = loc.source_scan.sources
            ElMessage.success('定位分析完成')
            
            if (loc.source_scan.power_map) {
                drawOfflineHeatmap(loc.source_scan)
            }
        }
    } catch (e) {
        ElMessage.error('定位分析失败: ' + (e.response?.data?.detail || e.message))
    } finally {
        processingOffline.value = false
    }
}

const drawOfflineHeatmap = (scanData) => {
    if (!canvasContext) return
    
    const ctx = canvasContext
    const width = 600
    const height = 600
    const powerMap = scanData.power_map
    const xCoords = scanData.x_coords
    const yCoords = scanData.y_coords
    
    drawGrid()
    
    const cellWidth = width / powerMap[0].length
    const cellHeight = height / powerMap.length
    
    for (let i = 0; i < powerMap.length; i++) {
        for (let j = 0; j < powerMap[i].length; j++) {
            const value = powerMap[i][j]
            if (value > 0.3) {
                const r = Math.floor(233 * value)
                const g = Math.floor(69 * value)
                const b = Math.floor(96 * value)
                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${value * 0.7})`
                ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth + 1, cellHeight + 1)
            }
        }
    }
}

watch(() => settings.value.scanRange, (newVal) => {
    scanRange.value = newVal
    initCanvas()
})

watch(() => settings.value.resolution, (newVal) => {
    resolution.value = newVal
    heatmapData = Array(newVal).fill().map(() => Array(newVal).fill(0))
})

onMounted(() => {
    initCanvas()
})

onUnmounted(() => {
    disconnectWebSocket()
    stopSimulation()
})
</script>

<style scoped>
.localization-container {
    max-width: 1600px;
    margin: 0 auto;
}

.header-card {
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

.main-row {
    margin-bottom: 20px;
}

.visualization-card,
.info-card,
.upload-card,
.control-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    margin-bottom: 20px;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: #e94560;
}

.visualization-wrapper {
    position: relative;
    width: 600px;
    height: 600px;
    margin: 0 auto;
    background: #0a0a0f;
    border-radius: 8px;
    overflow: hidden;
}

.heatmap-canvas {
    display: block;
    width: 100%;
    height: 100%;
}

.source-markers {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}

.source-marker {
    position: absolute;
    transform: translate(-50%, -50%);
}

.marker-pulse {
    position: absolute;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(233, 69, 96, 0.3);
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% {
        transform: translate(-50%, -50%) scale(0.5);
        opacity: 1;
    }
    100% {
        transform: translate(-50%, -50%) scale(2);
        opacity: 0;
    }
}

.marker-dot {
    width: 16px;
    height: 16px;
    background: #e94560;
    border-radius: 50%;
    border: 2px solid #ffffff;
    box-shadow: 0 0 10px rgba(233, 69, 96, 0.8);
}

.marker-label {
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    background: #e94560;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
}

.microphone-array {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}

.microphone {
    position: absolute;
    transform: translate(-50%, -50%);
    color: #409eff;
    font-size: 20px;
    filter: drop-shadow(0 0 5px rgba(64, 158, 255, 0.8));
}

.visualization-info {
    display: flex;
    justify-content: center;
    gap: 30px;
    margin-top: 15px;
    color: #8892b0;
    font-size: 14px;
}

.status-section h4,
.sources-section h4,
.history-section h4 {
    color: #ffffff;
    margin-bottom: 15px;
}

.sources-list {
    max-height: 200px;
    overflow-y: auto;
}

.source-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    background: rgba(15, 52, 96, 0.3);
    border-radius: 8px;
    margin-bottom: 8px;
}

.source-index {
    width: 24px;
    height: 24px;
    background: #e94560;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
}

.source-info {
    flex: 1;
}

.source-coords {
    color: #e0e0e0;
    font-size: 13px;
    margin-bottom: 5px;
}

.position-log {
    max-height: 150px;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    padding: 10px;
}

.log-item {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 12px;
    border-bottom: 1px solid rgba(136, 146, 176, 0.1);
}

.log-time {
    color: #8892b0;
}

.log-pos {
    color: #409eff;
    font-family: monospace;
}

.empty-history {
    color: #8892b0;
    text-align: center;
    padding: 20px;
    font-size: 13px;
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

:deep(.el-upload__text) {
    color: #8892b0;
}

:deep(.el-upload__text em) {
    color: #e94560;
    font-style: normal;
}

:deep(.el-upload__tip) {
    color: #8892b0;
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

:deep(.el-slider__runway) {
    background: #0f3460;
}

:deep(.el-slider__bar) {
    background: #e94560;
}

:deep(.el-slider__button) {
    border-color: #e94560;
}
</style>
