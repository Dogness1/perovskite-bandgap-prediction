<template>
  <view class="analysis-container page-container">
    <!-- Crystal Background -->
    <view class="crystal-bg"></view>

    <!-- Header -->
    <view class="page-header">
      <view class="header-icon">
        <text class="icon">📊</text>
      </view>
      <view class="header-text">
        <text class="title">数据分析</text>
        <text class="subtitle">Data Analysis</text>
      </view>
    </view>

    <!-- Tabs -->
    <view class="tabs">
      <view
        class="tab"
        v-for="tab in tabs"
        :key="tab.id"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <text class="tab-text">{{ tab.name }}</text>
      </view>
    </view>

    <!-- Content -->
    <view class="tab-content">
      <!-- Data Overview -->
      <view v-if="activeTab === 'overview'" class="overview-section">
        <view class="stats-grid">
          <view class="stat-card">
            <text class="stat-icon">📋</text>
            <text class="stat-label">样本总数</text>
            <text class="stat-value">{{ stats.total_samples || '加载中...' }}</text>
          </view>
          <view class="stat-card">
            <text class="stat-icon">⚡</text>
            <text class="stat-label">平均带隙</text>
            <text class="stat-value">{{ stats.bandgap_range?.mean?.toFixed(2) || '加载中...' }} eV</text>
          </view>
          <view class="stat-card">
            <text class="stat-icon">🔬</text>
            <text class="stat-label">A位元素</text>
            <text class="stat-value">{{ stats.elements?.A_sites?.length || 0 }}</text>
          </view>
          <view class="stat-card">
            <text class="stat-icon">🧪</text>
            <text class="stat-label">B位元素</text>
            <text class="stat-value">{{ stats.elements?.B_sites?.length || 0 }}</text>
          </view>
        </view>

        <view class="chart-section">
          <text class="chart-title">带隙分布</text>
          <view class="bandgap-chart">
            <canvas canvas-id="bandgapCanvas" class="chart-canvas"></canvas>
          </view>
        </view>

        <view class="chart-section">
          <text class="chart-title">卤素分布</text>
          <view class="halogen-chart">
            <canvas canvas-id="halogenCanvas" class="chart-canvas"></canvas>
          </view>
        </view>
      </view>

      <!-- Feature Importance -->
      <view v-if="activeTab === 'features'" class="features-section">
        <text class="section-title">特征重要性</text>
        <text class="section-desc">影响带隙预测的关键特征</text>

        <view class="importance-list" v-if="featureImportance.length > 0">
          <view class="importance-item" v-for="(item, index) in featureImportance" :key="index">
            <view class="importance-header">
              <text class="importance-rank">{{ index + 1 }}</text>
              <text class="importance-feature">{{ item.feature }}</text>
            </view>
            <view class="importance-bar">
              <view class="importance-fill" :style="{ width: (item.importance / maxImportance * 100) + '%' }"></view>
              <text class="importance-value">{{ (item.importance * 100).toFixed(2) }}%</text>
            </view>
          </view>
        </view>
        <view v-else class="loading-state">
          <text>加载中...</text>
        </view>
      </view>

      <!-- Halogen Effect -->
      <view v-if="activeTab === 'halogen'" class="halogen-section">
        <text class="section-title">卤素效应分析</text>
        <text class="section-desc">不同卤素对带隙的影响</text>

        <view class="halogen-effect-card">
          <view class="halogen-item cl">
            <text class="halogen-symbol">Cl</text>
            <text class="halogen-name">氯</text>
            <text class="halogen-bandgap">3.26 eV</text>
            <text class="halogen-desc">高带隙，适合紫外应用</text>
          </view>
          <view class="halogen-item br">
            <text class="halogen-symbol">Br</text>
            <text class="halogen-name">溴</text>
            <text class="halogen-bandgap">2.81 eV</text>
            <text class="halogen-desc">中等带隙，平衡性能</text>
          </view>
          <view class="halogen-item i">
            <text class="halogen-symbol">I</text>
            <text class="halogen-name">碘</text>
            <text class="halogen-bandgap">2.37 eV</text>
            <text class="halogen-desc">低带隙，适合太阳能应用</text>
          </view>
        </view>

        <view class="effect-chart">
          <canvas canvas-id="effectCanvas" class="chart-canvas"></canvas>
        </view>
      </view>

      <!-- Structure Analysis -->
      <view v-if="activeTab === 'structure'" class="structure-section">
        <text class="section-title">结构分析</text>
        <text class="section-desc">分析生成结构与数据集对比</text>

        <view class="analysis-form">
          <view class="input-group">
            <text class="input-label">输入结构</text>
            <input v-model="structureInput" type="text" class="structure-input" placeholder="例如: CsPbCl_1Br_1I_1" />
          </view>
          <button class="analyze-btn" @click="analyzeStructure">
            <text class="btn-text">分析结构</text>
          </button>
        </view>

        <view class="analysis-result" v-if="analysisResult">
          <view class="result-card">
            <text class="result-title">分析结果</text>
            <view class="result-content">
              <text class="result-item"><text class="result-label">结构:</text> {{ analysisResult.structure?.formula }}</text>
              <text class="result-item"><text class="result-label">带隙:</text> {{ analysisResult.structure?.predicted_bandgap?.toFixed(2) }} eV</text>
              <text class="result-item"><text class="result-label">相似结构:</text> {{ analysisResult.similar_structures?.length }} 个</text>
              <text class="result-item"><text class="result-label">平均相似度:</text> {{ analysisResult.average_similarity?.toFixed(2) }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index.js'

export default {
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', name: '数据概览' },
        { id: 'features', name: '特征重要性' },
        { id: 'halogen', name: '卤素效应' },
        { id: 'structure', name: '结构分析' }
      ],
      stats: {},
      distribution: {},
      featureImportance: [],
      maxImportance: 0,
      structureInput: '',
      analysisResult: null
    }
  },

  onLoad(options) {
    if (options.formula) {
      this.structureInput = options.formula
      this.activeTab = 'structure'
      this.analyzeStructure()
    }
    this.loadData()
  },

  methods: {
    async loadData() {
      try {
        // 加载统计数据
        const statsData = await api.getDataStats()
        this.stats = statsData

        // 加载分布数据
        const distributionData = await api.getDataDistribution()
        this.distribution = distributionData

        // 加载特征重要性
        const importanceData = await api.getFeatureImportance()
        this.featureImportance = importanceData.feature_importance || []
        if (this.featureImportance.length > 0) {
          this.maxImportance = Math.max(...this.featureImportance.map(item => item.importance))
        }

        // 绘制图表
        this.$nextTick(() => {
          this.drawBandgapChart()
          this.drawHalogenChart()
          this.drawEffectChart()
        })

      } catch (error) {
        console.error('加载数据失败:', error)
        // 使用模拟数据
        this.loadMockData()
      }
    },

    loadMockData() {
      // 模拟统计数据
      this.stats = {
        total_samples: 488,
        bandgap_range: {
          min: 1.5,
          max: 3.5,
          mean: 2.3,
          std: 0.4
        },
        elements: {
          A_sites: ['MA', 'FA', 'Cs', 'Rb', 'K'],
          B_sites: ['Ge', 'Sn', 'Pb', 'Ca', 'Sr', 'Ba']
        }
      }

      // 模拟特征重要性
      this.featureImportance = [
        { feature: 'I_ratio', importance: 0.35 },
        { feature: 'Br_ratio', importance: 0.25 },
        { feature: 'Cl_ratio', importance: 0.20 },
        { feature: 'B_Pb', importance: 0.10 },
        { feature: 'A_Cs', importance: 0.05 },
        { feature: 'A_MA', importance: 0.03 },
        { feature: 'A_FA', importance: 0.02 }
      ]
      this.maxImportance = 0.35

      // 模拟分布数据
      this.distribution = {
        halogen_distribution: { Cl: 120, Br: 180, I: 188 },
        bandgap_histogram: {
          bins: [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
          counts: [0, 0, 20, 80, 150, 120, 80, 30, 8, 0, 0, 0]
        }
      }

      // 绘制图表
      this.$nextTick(() => {
        this.drawBandgapChart()
        this.drawHalogenChart()
        this.drawEffectChart()
      })
    },

    drawBandgapChart() {
      const ctx = uni.createCanvasContext('bandgapCanvas', this)
      const canvasWidth = 700
      const canvasHeight = 300
      const padding = 40

      ctx.clearRect(0, 0, canvasWidth, canvasHeight)

      // 绘制标题
      ctx.setFontSize(20)
      ctx.setFillStyle('#f9fafb')
      ctx.fillText('带隙分布', 20, 30)

      // 绘制坐标轴
      ctx.setStrokeStyle('#374151')
      ctx.setLineWidth(2)
      ctx.beginPath()
      ctx.moveTo(padding, padding)
      ctx.lineTo(padding, canvasHeight - padding)
      ctx.lineTo(canvasWidth - padding, canvasHeight - padding)
      ctx.stroke()

      // 绘制柱状图
      const data = this.distribution.bandgap_histogram?.counts || [0, 20, 50, 80, 120, 100, 60, 30, 10, 5, 0, 0]
      const binWidth = (canvasWidth - 2 * padding) / data.length
      const maxCount = Math.max(...data)

      data.forEach((count, index) => {
        const x = padding + index * binWidth
        const height = (count / maxCount) * (canvasHeight - 2 * padding)
        const y = canvasHeight - padding - height

        // 渐变色填充
        const gradient = ctx.createLinearGradient(x, y, x, canvasHeight - padding)
        gradient.addColorStop(0, '#00d4ff')
        gradient.addColorStop(1, '#8b5cf6')
        ctx.setFillStyle(gradient)
        ctx.fillRect(x + 2, y, binWidth - 4, height)

        // 绘制数值
        ctx.setFontSize(12)
        ctx.setFillStyle('#9ca3af')
        ctx.fillText(count, x + binWidth / 2 - 10, y - 10)
      })

      // 绘制X轴标签
      const bins = this.distribution.bandgap_histogram?.bins || [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
      bins.forEach((bin, index) => {
        if (index < bins.length - 1) {
          const x = padding + index * binWidth + binWidth / 2
          ctx.setFontSize(12)
          ctx.setFillStyle('#9ca3af')
          ctx.fillText(bin.toFixed(1), x - 10, canvasHeight - padding + 20)
        }
      })

      ctx.draw()
    },

    drawHalogenChart() {
      const ctx = uni.createCanvasContext('halogenCanvas', this)
      const canvasWidth = 700
      const canvasHeight = 300
      const padding = 40

      ctx.clearRect(0, 0, canvasWidth, canvasHeight)

      // 绘制标题
      ctx.setFontSize(20)
      ctx.setFillStyle('#f9fafb')
      ctx.fillText('卤素分布', 20, 30)

      // 绘制饼图
      const data = this.distribution.halogen_distribution || { Cl: 120, Br: 180, I: 188 }
      const labels = Object.keys(data)
      const values = Object.values(data)
      const total = values.reduce((sum, value) => sum + value, 0)

      const colors = ['#00d4ff', '#8b5cf6', '#10b981']
      let startAngle = -Math.PI / 2

      values.forEach((value, index) => {
        const angle = (value / total) * 2 * Math.PI
        
        // 绘制扇形
        ctx.setFillStyle(colors[index])
        ctx.beginPath()
        ctx.moveTo(canvasWidth / 2, canvasHeight / 2)
        ctx.arc(canvasWidth / 2, canvasHeight / 2, 100, startAngle, startAngle + angle)
        ctx.closePath()
        ctx.fill()

        // 绘制标签
        const midAngle = startAngle + angle / 2
        const x = canvasWidth / 2 + Math.cos(midAngle) * 130
        const y = canvasHeight / 2 + Math.sin(midAngle) * 130
        
        ctx.setFontSize(16)
        ctx.setFillStyle('#f9fafb')
        ctx.fillText(`${labels[index]}: ${value}`, x, y)

        startAngle += angle
      })

      ctx.draw()
    },

    drawEffectChart() {
      const ctx = uni.createCanvasContext('effectCanvas', this)
      const canvasWidth = 700
      const canvasHeight = 300
      const padding = 40

      ctx.clearRect(0, 0, canvasWidth, canvasHeight)

      // 绘制标题
      ctx.setFontSize(20)
      ctx.setFillStyle('#f9fafb')
      ctx.fillText('卤素比例对带隙的影响', 20, 30)

      // 绘制坐标轴
      ctx.setStrokeStyle('#374151')
      ctx.setLineWidth(2)
      ctx.beginPath()
      ctx.moveTo(padding, padding)
      ctx.lineTo(padding, canvasHeight - padding)
      ctx.lineTo(canvasWidth - padding, canvasHeight - padding)
      ctx.stroke()

      // 模拟数据：I比例从0到1，带隙从3.26到2.37
      const points = []
      for (let i = 0; i <= 10; i++) {
        const iRatio = i / 10
        const bandgap = 3.26 - (3.26 - 2.37) * iRatio
        points.push({ x: iRatio, y: bandgap })
      }

      // 绘制曲线
      ctx.setStrokeStyle('#8b5cf6')
      ctx.setLineWidth(3)
      ctx.beginPath()
      points.forEach((point, index) => {
        const x = padding + point.x * (canvasWidth - 2 * padding)
        const y = canvasHeight - padding - (point.y - 2) * (canvasHeight - 2 * padding) / 1.5
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // 绘制数据点
      points.forEach(point => {
        const x = padding + point.x * (canvasWidth - 2 * padding)
        const y = canvasHeight - padding - (point.y - 2) * (canvasHeight - 2 * padding) / 1.5
        
        ctx.setFillStyle('#8b5cf6')
        ctx.beginPath()
        ctx.arc(x, y, 5, 0, 2 * Math.PI)
        ctx.fill()
      })

      // 绘制标签
      ctx.setFontSize(12)
      ctx.setFillStyle('#9ca3af')
      ctx.fillText('I比例', canvasWidth - padding - 30, canvasHeight - padding + 20)
      ctx.save()
      ctx.translate(padding - 30, canvasHeight / 2)
      ctx.rotate(-Math.PI / 2)
      ctx.fillText('带隙 (eV)', 0, 0)
      ctx.restore()

      ctx.draw()
    },

    async analyzeStructure() {
      if (!this.structureInput) return

      try {
        const response = await api.analyzeStructure({
          generated_structure: {
            formula: this.structureInput,
            predicted_bandgap: 2.0
          }
        })
        this.analysisResult = response
      } catch (error) {
        console.error('分析失败:', error)
        // 模拟分析结果
        this.analysisResult = {
          structure: {
            formula: this.structureInput,
            predicted_bandgap: 2.0
          },
          similar_structures: [
            { formula: 'CsPbCl_0.9Br_1.1I_1.0', bandgap: 2.05 },
            { formula: 'CsPbCl_1.1Br_0.9I_1.0', bandgap: 2.10 },
            { formula: 'CsPbCl_1.0Br_1.0I_1.0', bandgap: 2.00 }
          ],
          average_similarity: 0.95
        }
      }
    }
  }
}
</script>

<style scoped>
.analysis-container {
  min-height: 100vh;
  padding: 32rpx;
  padding-bottom: 140rpx;
}

/* Page Header */
.page-header {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 32rpx;
}

.header-icon {
  width: 80rpx;
  height: 80rpx;
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon {
  font-size: 40rpx;
}

.header-text {
  flex: 1;
}

.title {
  font-size: 40rpx;
  font-weight: 700;
  color: #f9fafb;
  display: block;
}

.subtitle {
  font-size: 22rpx;
  color: #6b7280;
}

/* Tabs */
.tabs {
  display: flex;
  background: #111827;
  border-radius: 16rpx;
  padding: 8rpx;
  margin-bottom: 32rpx;
  border: 1px solid #374151;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 16rpx;
  border-radius: 12rpx;
  transition: all 0.3s ease;
}

.tab.active {
  background: linear-gradient(135deg, #10b981, #059669);
}

.tab-text {
  font-size: 24rpx;
  font-weight: 500;
  color: #9ca3af;
}

.tab.active .tab-text {
  color: #ffffff;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.stat-card {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  border: 1px solid #374151;
  text-align: center;
  transition: all 0.3s ease;
}

.stat-card:hover {
  border-color: #10b981;
  box-shadow: 0 4rpx 20rpx rgba(16, 185, 129, 0.1);
}

.stat-icon {
  font-size: 40rpx;
  display: block;
  margin-bottom: 12rpx;
}

.stat-label {
  font-size: 22rpx;
  color: #6b7280;
  display: block;
  margin-bottom: 8rpx;
}

.stat-value {
  font-size: 32rpx;
  font-weight: 700;
  color: #f9fafb;
  display: block;
}

/* Chart Section */
.chart-section {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  border: 1px solid #374151;
}

.chart-title {
  font-size: 24rpx;
  font-weight: 600;
  color: #f9fafb;
  margin-bottom: 20rpx;
  display: block;
}

.chart-canvas {
  width: 100%;
  height: 300rpx;
}

/* Features Section */
.features-section {
  padding: 0 8rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
  display: block;
  margin-bottom: 8rpx;
}

.section-desc {
  font-size: 22rpx;
  color: #6b7280;
  display: block;
  margin-bottom: 24rpx;
}

.importance-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.importance-item {
  background: #111827;
  border-radius: 16rpx;
  padding: 20rpx;
  border: 1px solid #374151;
}

.importance-header {
  display: flex;
  align-items: center;
  margin-bottom: 12rpx;
}

.importance-rank {
  width: 40rpx;
  height: 40rpx;
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 8rpx;
  font-size: 22rpx;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
}

.importance-feature {
  font-size: 24rpx;
  color: #f9fafb;
  flex: 1;
}

.importance-bar {
  position: relative;
  height: 24rpx;
  background: #1f2937;
  border-radius: 12rpx;
  overflow: hidden;
}

.importance-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  border-radius: 12rpx;
  transition: width 0.5s ease;
}

.importance-value {
  position: absolute;
  right: 12rpx;
  top: 50%;
  transform: translateY(-50%);
  font-size: 20rpx;
  color: #f9fafb;
  font-weight: 500;
}

/* Halogen Section */
.halogen-effect-card {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.halogen-item {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  border: 1px solid #374151;
  text-align: center;
  transition: all 0.3s ease;
}

.halogen-item.cl:hover {
  border-color: #00d4ff;
  box-shadow: 0 4rpx 20rpx rgba(0, 212, 255, 0.1);
}

.halogen-item.br:hover {
  border-color: #8b5cf6;
  box-shadow: 0 4rpx 20rpx rgba(139, 92, 246, 0.1);
}

.halogen-item.i:hover {
  border-color: #10b981;
  box-shadow: 0 4rpx 20rpx rgba(16, 185, 129, 0.1);
}

.halogen-symbol {
  font-size: 48rpx;
  font-weight: 700;
  display: block;
  margin-bottom: 8rpx;
}

.halogen-item.cl .halogen-symbol {
  color: #00d4ff;
}

.halogen-item.br .halogen-symbol {
  color: #8b5cf6;
}

.halogen-item.i .halogen-symbol {
  color: #10b981;
}

.halogen-name {
  font-size: 22rpx;
  color: #6b7280;
  display: block;
  margin-bottom: 8rpx;
}

.halogen-bandgap {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
  display: block;
  margin-bottom: 8rpx;
}

.halogen-desc {
  font-size: 20rpx;
  color: #9ca3af;
  display: block;
}

.effect-chart {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  border: 1px solid #374151;
}

/* Structure Analysis */
.analysis-form {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  border: 1px solid #374151;
}

.input-group {
  margin-bottom: 20rpx;
}

.input-label {
  font-size: 24rpx;
  color: #9ca3af;
  margin-bottom: 12rpx;
  display: block;
}

.structure-input {
  width: 100%;
  height: 80rpx;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12rpx;
  color: #f9fafb;
  font-size: 24rpx;
  padding: 0 20rpx;
  font-family: 'Courier New', monospace;
}

.analyze-btn {
  width: 100%;
  height: 80rpx;
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  border-radius: 12rpx;
  font-size: 28rpx;
  font-weight: 600;
  color: #ffffff;
}

.analysis-result {
  margin-top: 24rpx;
}

.result-card {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  border: 1px solid #374151;
}

.result-title {
  font-size: 24rpx;
  font-weight: 600;
  color: #f9fafb;
  margin-bottom: 16rpx;
  display: block;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.result-item {
  font-size: 22rpx;
  color: #f9fafb;
}

.result-label {
  color: #9ca3af;
  margin-right: 12rpx;
}

/* Loading State */
.loading-state {
  text-align: center;
  padding: 40rpx;
  color: #6b7280;
  font-size: 24rpx;
}
</style>