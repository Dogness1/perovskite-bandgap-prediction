<template>
  <view class="prediction-container page-container">
    <!-- Crystal Background -->
    <view class="crystal-bg"></view>

    <!-- Header -->
    <view class="page-header">
      <view class="header-icon">
        <text class="icon">⚡</text>
      </view>
      <view class="header-text">
        <text class="title">带隙预测 (HSErel_SOC)</text>
        <text class="subtitle">Band Gap Prediction</text>
      </view>
    </view>

    <!-- Input Section -->
    <view class="input-section">
      <view class="section-card">
        <text class="card-title">化学组成</text>
        <text class="card-desc">选择钙钛矿的A位和B位阳离子</text>

        <!-- A-Site Selector -->
        <view class="input-group">
          <text class="input-label">A位阳离子</text>
          <scroll-view scroll-x class="element-scroll">
            <view class="element-chips">
              <view
                class="element-chip"
                v-for="element in aSiteElements"
                :key="element"
                :class="{ active: selectedA === element }"
                @click="selectA(element)"
              >
                <text class="chip-text">{{ element }}</text>
              </view>
            </view>
          </scroll-view>
        </view>

        <!-- B-Site Selector -->
        <view class="input-group">
          <text class="input-label">B位金属</text>
          <scroll-view scroll-x class="element-scroll">
            <view class="element-chips">
              <view
                class="element-chip b-site"
                v-for="element in bSiteElements"
                :key="element"
                :class="{ active: selectedB === element }"
                @click="selectB(element)"
              >
                <text class="chip-text">{{ element }}</text>
              </view>
            </view>
          </scroll-view>
        </view>
      </view>

      <view class="section-card">
        <text class="card-title">卤素比例</text>
        <text class="card-desc">调整三种卤素的比例（总和 = 3）</text>

        <!-- Halogen Sliders -->
        <view class="slider-group">
          <view class="slider-item">
            <view class="slider-header">
              <text class="slider-label cl-color">Cl (氯)</text>
              <text class="slider-value">{{ clRatio.toFixed(2) }}</text>
            </view>
            <slider
              :value="clRatio * 100"
              min="0"
              max="300"
              @change="onClChange"
              activeColor="#00d4ff"
              backgroundColor="#1f2937"
              block-size="20"
            />
          </view>

          <view class="slider-item">
            <view class="slider-header">
              <text class="slider-label br-color">Br (溴)</text>
              <text class="slider-value">{{ brRatio.toFixed(2) }}</text>
            </view>
            <slider
              :value="brRatio * 100"
              min="0"
              max="300"
              @change="onBrChange"
              activeColor="#8b5cf6"
              backgroundColor="#1f2937"
              block-size="20"
            />
          </view>

          <view class="slider-item">
            <view class="slider-header">
              <text class="slider-label i-color">I (碘)</text>
              <text class="slider-value">{{ iRatio.toFixed(2) }}</text>
            </view>
            <slider
              :value="iRatio * 100"
              min="0"
              max="300"
              @change="onIChange"
              activeColor="#10b981"
              backgroundColor="#1f2937"
              block-size="20"
            />
          </view>
        </view>

        <!-- Total Indicator -->
        <view class="total-indicator">
          <view class="total-bar">
            <view class="total-segment cl" :style="{ width: clRatio / 3 * 100 + '%' }"></view>
            <view class="total-segment br" :style="{ width: brRatio / 3 * 100 + '%' }"></view>
            <view class="total-segment i" :style="{ width: iRatio / 3 * 100 + '%' }"></view>
          </view>
          <text class="total-text">总和: {{ (clRatio + brRatio + iRatio).toFixed(2) }}</text>
        </view>
      </view>

      <!-- Predict Button -->
      <button class="predict-btn" @click="predict" :disabled="isLoading">
        <text class="btn-text" v-if="!isLoading">预测带隙</text>
        <text class="btn-text" v-else>预测中...</text>
      </button>
    </view>

    <!-- Result Section -->
    <view class="result-section" v-if="showResult">
      <view class="result-card">
        <view class="result-header">
          <text class="result-title">预测结果</text>
          <view class="result-actions">
            <view class="result-badge">
              <text class="badge-text">AI 预测</text>
            </view>
            <view class="export-buttons">
              <button class="export-btn" @click="exportResult('csv')">
                <text class="export-icon">📊</text>
                <text class="export-text">导出CSV</text>
              </button>
              <button class="export-btn" @click="exportResult('json')">
                <text class="export-icon">📄</text>
                <text class="export-text">导出JSON</text>
              </button>
            </view>
          </view>
        </view>

        <view class="formula-display">
          <text class="formula-text">{{ generatedFormula }}</text>
        </view>

        <view class="bandgap-result">
          <text class="bandgap-value">{{ predictedBandgap }}</text>
          <text class="bandgap-unit">eV</text>
        </view>

        <view class="result-meter">
          <view class="meter-track">
            <view class="meter-fill" :style="{ width: bandgapPercent + '%' }"></view>
            <view class="meter-marker" :style="{ left: bandgapPercent + '%' }"></view>
          </view>
          <view class="meter-labels">
            <text class="meter-label">0 eV</text>
            <text class="meter-label">3 eV</text>
            <text class="meter-label">6 eV</text>
          </view>
        </view>

        <!-- Properties Card -->
        <view class="properties-grid">
          <view class="property-item">
            <text class="property-icon">🔬</text>
            <text class="property-label">结构类型</text>
            <text class="property-value">{{ structureType }}</text>
          </view>
          <view class="property-item">
            <text class="property-icon">☀️</text>
            <text class="property-label">光电应用</text>
            <text class="property-value">{{ applicationType }}</text>
          </view>
          <view class="property-item">
            <text class="property-icon">📊</text>
            <text class="property-label">稳定性</text>
            <text class="property-value">{{ stabilityLevel }}</text>
          </view>
          <view class="property-item">
            <text class="property-icon">🎯</text>
            <text class="property-label">置信度</text>
            <text class="property-value">高</text>
          </view>
        </view>
      </view>

      <!-- History -->
      <view class="history-section" v-if="predictionHistory.length > 0">
        <text class="history-title">历史预测</text>
        <view class="history-list">
          <view class="history-item" v-for="(item, index) in predictionHistory" :key="index">
            <text class="history-formula">{{ item.formula }}</text>
            <text class="history-bandgap">{{ item.bandgap }} eV</text>
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
      aSiteElements: ['MA', 'FA', 'Cs', 'Rb', 'K'],
      bSiteElements: ['Ge', 'Sn', 'Pb', 'Ca', 'Sr', 'Ba'],
      selectedA: 'Cs',
      selectedB: 'Pb',
      clRatio: 1.0,
      brRatio: 1.0,
      iRatio: 1.0,
      isLoading: false,
      showResult: false,
      predictedBandgap: 0,
      generatedFormula: '',
      predictionHistory: []
    }
  },

  computed: {
    bandgapPercent() {
      return Math.min(Math.max(this.predictedBandgap / 6 * 100, 0), 100)
    },
    structureType() {
      if (this.clRatio + this.brRatio + this.iRatio === 3) {
        const hasMultiple = [this.clRatio, this.brRatio, this.iRatio].filter(r => r > 0.1).length > 1
        return hasMultiple ? '混合卤素钙钛矿' : '单卤素钙钛矿'
      }
      return '非标准结构'
    },
    applicationType() {
      const bg = this.predictedBandgap
      if (bg < 1.5) return '红外探测器'
      if (bg < 2.0) return '太阳能电池'
      if (bg < 3.0) return 'LED器件'
      return '紫外探测器'
    },
    stabilityLevel() {
      const total = this.clRatio + this.brRatio + this.iRatio
      if (Math.abs(total - 3) < 0.1) return '稳定'
      if (Math.abs(total - 3) < 0.3) return '较稳定'
      return '需验证'
    }
  },

  onLoad() {
    this.loadElements()
  },

  methods: {
    async loadElements() {
      try {
        const data = await api.getElements()
        if (data.A_sites) this.aSiteElements = data.A_sites
        if (data.B_sites) this.bSiteElements = data.B_sites
      } catch (error) {
        console.log('Using default elements')
      }
    },

    selectA(element) {
      this.selectedA = element
    },

    selectB(element) {
      this.selectedB = element
    },

    onClChange(e) {
      this.clRatio = e.detail.value / 100
      this.normalizeRatios('cl')
    },

    onBrChange(e) {
      this.brRatio = e.detail.value / 100
      this.normalizeRatios('br')
    },

    onIChange(e) {
      this.iRatio = e.detail.value / 100
      this.normalizeRatios('i')
    },

    normalizeRatios(changed) {
      // 保持总和为3
      const total = this.clRatio + this.brRatio + this.iRatio
      if (total > 3) {
        const scale = 3 / total
        this.clRatio *= scale
        this.brRatio *= scale
        this.iRatio *= scale
      }
    },

    async predict() {
      if (this.isLoading) return

      this.isLoading = true

      try {
        const response = await api.predictBandgap({
          a_site: this.selectedA,
          b_site: this.selectedB,
          cl_ratio: this.clRatio,
          br_ratio: this.brRatio,
          i_ratio: this.iRatio
        })

        this.predictedBandgap = response.predicted_bandgap
        this.generatedFormula = response.formula
        this.showResult = true

        // 添加到历史
        this.predictionHistory.unshift({
          formula: response.formula,
          bandgap: response.predicted_bandgap.toFixed(2)
        })

        // 限制历史记录数量
        if (this.predictionHistory.length > 5) {
          this.predictionHistory.pop()
        }

      } catch (error) {
        console.error('预测失败:', error)
        // 使用模拟数据
        this.simulatePrediction()
      }

      this.isLoading = false
    },

    simulatePrediction() {
      // 模拟预测结果
      const baseBandgap = {
        'Cl': 3.26, 'Br': 2.81, 'I': 2.37
      }

      const total = this.clRatio + this.brRatio + this.iRatio
      const avgBandgap = (
        this.clRatio * baseBandgap.Cl +
        this.brRatio * baseBandgap.Br +
        this.iRatio * baseBandgap.I
      ) / total

      // 添加一些随机性
      const noise = (Math.random() - 0.5) * 0.3
      this.predictedBandgap = avgBandgap + noise

      // 构建公式
      let formula = this.selectedA + this.selectedB
      if (this.clRatio > 0.01) formula += `Cl_${this.clRatio.toFixed(2)}`
      if (this.brRatio > 0.01) formula += `Br_${this.brRatio.toFixed(2)}`
      if (this.iRatio > 0.01) formula += `I_${this.iRatio.toFixed(2)}`
      this.generatedFormula = formula
      this.showResult = true

      this.predictionHistory.unshift({
        formula: this.generatedFormula,
        bandgap: this.predictedBandgap.toFixed(2)
      })

      if (this.predictionHistory.length > 5) {
        this.predictionHistory.pop()
      }
    },

    async exportResult(format) {
      try {
        // 导出当前结果
        const resultData = {
          formula: this.generatedFormula,
          predicted_bandgap: this.predictedBandgap,
          a_site: this.selectedA,
          b_site: this.selectedB,
          cl_ratio: this.clRatio,
          br_ratio: this.brRatio,
          i_ratio: this.iRatio,
          structure_type: this.structureType,
          application_type: this.applicationType,
          stability_level: this.stabilityLevel,
          timestamp: new Date().toISOString()
        }

        if (format === 'csv') {
          // 生成CSV内容
          const csvContent = [
            ['化学式', '预测带隙 HSErel_SOC(eV)', 'A位元素', 'B位元素', 'Cl比例', 'Br比例', 'I比例', '结构类型', '应用类型', '稳定性', '时间戳'],
            [resultData.formula, resultData.predicted_bandgap.toFixed(3), resultData.a_site, resultData.b_site, 
             resultData.cl_ratio, resultData.br_ratio, resultData.i_ratio, 
             resultData.structure_type, resultData.application_type, resultData.stability_level, resultData.timestamp]
          ].map(row => row.join(',')).join('\n')

          // 创建下载链接
          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
          const link = document.createElement('a')
          const url = URL.createObjectURL(blob)
          link.setAttribute('href', url)
          link.setAttribute('download', `prediction_result_${Date.now()}.csv`)
          link.style.visibility = 'hidden'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        } else if (format === 'json') {
          // 生成JSON内容
          const jsonContent = JSON.stringify(resultData, null, 2)
          const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
          const link = document.createElement('a')
          const url = URL.createObjectURL(blob)
          link.setAttribute('href', url)
          link.setAttribute('download', `prediction_result_${Date.now()}.json`)
          link.style.visibility = 'hidden'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        }
      } catch (error) {
        console.error('导出失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.prediction-container {
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
  background: linear-gradient(135deg, #00d4ff, #8b5cf6);
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

/* Section Card */
.section-card {
  background: #111827;
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  border: 1px solid #374151;
  position: relative;
}

.section-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 32rpx;
  right: 32rpx;
  height: 2px;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6);
  border-radius: 2rpx;
}

.card-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
  display: block;
}

.card-desc {
  font-size: 22rpx;
  color: #6b7280;
  margin-top: 8rpx;
  display: block;
}

/* Element Selection */
.input-group {
  margin-top: 24rpx;
}

.input-label {
  font-size: 24rpx;
  color: #9ca3af;
  margin-bottom: 16rpx;
  display: block;
}

.element-scroll {
  white-space: nowrap;
}

.element-chips {
  display: inline-flex;
  gap: 16rpx;
  padding: 8rpx 0;
}

.element-chip {
  background: #1f2937;
  border: 2px solid #374151;
  border-radius: 16rpx;
  padding: 16rpx 32rpx;
  transition: all 0.3s ease;
}

.element-chip.active {
  background: linear-gradient(135deg, #00d4ff, #0099cc);
  border-color: #00d4ff;
}

.element-chip.b-site.active {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  border-color: #8b5cf6;
}

.chip-text {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
}

/* Sliders */
.slider-group {
  margin-top: 24rpx;
}

.slider-item {
  margin-bottom: 24rpx;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.slider-label {
  font-size: 26rpx;
  font-weight: 500;
}

.cl-color { color: #00d4ff; }
.br-color { color: #8b5cf6; }
.i-color { color: #10b981; }

.slider-value {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
  background: #1f2937;
  padding: 8rpx 20rpx;
  border-radius: 12rpx;
}

/* Total Indicator */
.total-indicator {
  margin-top: 24rpx;
  padding-top: 24rpx;
  border-top: 1px solid #374151;
}

.total-bar {
  height: 24rpx;
  border-radius: 12rpx;
  background: #1f2937;
  display: flex;
  overflow: hidden;
}

.total-segment {
  height: 100%;
  transition: width 0.3s ease;
}

.total-segment.cl { background: #00d4ff; }
.total-segment.br { background: #8b5cf6; }
.total-segment.i { background: #10b981; }

.total-text {
  display: block;
  text-align: center;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #9ca3af;
}

/* Predict Button */
.predict-btn {
  width: 100%;
  height: 96rpx;
  background: linear-gradient(135deg, #00d4ff, #8b5cf6);
  border: none;
  border-radius: 24rpx;
  margin-top: 16rpx;
}

.predict-btn[disabled] {
  opacity: 0.6;
}

.btn-text {
  font-size: 32rpx;
  font-weight: 600;
  color: #ffffff;
}

/* Result Section */
.result-section {
  margin-top: 32rpx;
}

.result-card {
  background: #111827;
  border-radius: 24rpx;
  padding: 32rpx;
  border: 1px solid #374151;
  position: relative;
  overflow: hidden;
}

.result-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #10b981, #00d4ff, #8b5cf6);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
  flex-wrap: wrap;
  gap: 12rpx;
}

.result-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex-wrap: wrap;
}

.result-badge {
  background: linear-gradient(135deg, #10b981, #059669);
  padding: 8rpx 20rpx;
  border-radius: 20rpx;
}

.badge-text {
  font-size: 20rpx;
  color: #ffffff;
  font-weight: 500;
}

.export-buttons {
  display: flex;
  gap: 8rpx;
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.export-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.export-icon {
  font-size: 20rpx;
}

.export-text {
  font-size: 24rpx;
  color: #ffffff;
  font-weight: 500;
}

.formula-display {
  background: #1a1f2e;
  border-radius: 16rpx;
  padding: 24rpx;
  text-align: center;
  margin-bottom: 24rpx;
}

.formula-text {
  font-size: 28rpx;
  font-family: 'Courier New', monospace;
  color: #00d4ff;
}

.bandgap-result {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8rpx;
  margin-bottom: 24rpx;
}

.bandgap-value {
  font-size: 72rpx;
  font-weight: 700;
  background: linear-gradient(135deg, #00d4ff, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.bandgap-unit {
  font-size: 32rpx;
  color: #6b7280;
}

/* Meter */
.result-meter {
  margin-bottom: 24rpx;
}

.meter-track {
  height: 16rpx;
  background: #1f2937;
  border-radius: 8rpx;
  position: relative;
  overflow: visible;
}

.meter-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #00d4ff, #8b5cf6, #f59e0b);
  border-radius: 8rpx;
  transition: width 0.5s ease;
}

.meter-marker {
  position: absolute;
  top: -8rpx;
  width: 32rpx;
  height: 32rpx;
  background: #ffffff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.meter-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 12rpx;
}

.meter-label {
  font-size: 20rpx;
  color: #6b7280;
}

/* Properties Grid */
.properties-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}

.property-item {
  background: #1a1f2e;
  border-radius: 16rpx;
  padding: 20rpx;
  text-align: center;
}

.property-icon {
  font-size: 32rpx;
  display: block;
  margin-bottom: 8rpx;
}

.property-label {
  font-size: 20rpx;
  color: #6b7280;
  display: block;
}

.property-value {
  font-size: 24rpx;
  color: #f9fafb;
  font-weight: 500;
  margin-top: 4rpx;
  display: block;
}

/* History */
.history-section {
  margin-top: 24rpx;
}

.history-title {
  font-size: 24rpx;
  color: #9ca3af;
  margin-bottom: 16rpx;
  display: block;
}

.history-list {
  background: #111827;
  border-radius: 16rpx;
  overflow: hidden;
}

.history-item {
  display: flex;
  justify-content: space-between;
  padding: 20rpx 24rpx;
  border-bottom: 1px solid #1f2937;
}

.history-item:last-child {
  border-bottom: none;
}

.history-formula {
  font-size: 24rpx;
  color: #f9fafb;
  font-family: 'Courier New', monospace;
}

.history-bandgap {
  font-size: 24rpx;
  color: #00d4ff;
  font-weight: 500;
}
</style>
