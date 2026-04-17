<template>
  <view class="generator-container page-container">
    <!-- Crystal Background -->
    <view class="crystal-bg"></view>

    <!-- Header -->
    <view class="page-header">
      <view class="header-icon">
        <text class="icon">🧪</text>
      </view>
      <view class="header-text">
        <text class="title">结构生成</text>
        <text class="subtitle">Structure Generator</text>
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
        <text class="card-title">生成参数</text>
        <text class="card-desc">设置目标带隙和生成数量</text>

        <!-- Target Bandgap -->
        <view class="input-group">
          <text class="input-label">目标带隙 (eV)</text>
          <view class="slider-with-input">
            <slider
              :value="targetBandgap * 100"
              min="100"
              max="300"
              @change="onBandgapChange"
              activeColor="#8b5cf6"
              backgroundColor="#1f2937"
              block-size="20"
            />
            <input
              v-model="targetBandgap"
              type="number"
              step="0.1"
              min="1.0"
              max="3.0"
              class="bandgap-input"
              @change="onBandgapInput"
            />
          </view>
        </view>

        <!-- Number of Samples -->
        <view class="input-group">
          <text class="input-label">生成数量</text>
          <view class="number-input">
            <button class="number-btn" @click="decreaseSamples" :disabled="nSamples <= 1">-</button>
            <text class="number-value">{{ nSamples }}</text>
            <button class="number-btn" @click="increaseSamples" :disabled="nSamples >= 20">+</button>
          </view>
        </view>

        <!-- Tolerance -->
        <view class="input-group">
          <text class="input-label">带隙容差 (eV)</text>
          <view class="tolerance-options">
            <view
              class="tolerance-option"
              v-for="tolerance in toleranceOptions"
              :key="tolerance"
              :class="{ active: bandgapTolerance === tolerance }"
              @click="selectTolerance(tolerance)"
            >
              <text class="tolerance-text">{{ tolerance }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Generate Button -->
      <button class="generate-btn" @click="generate" :disabled="isLoading">
        <text class="btn-text" v-if="!isLoading">生成结构</text>
        <text class="btn-text" v-else>生成中...</text>
      </button>
    </view>

    <!-- Result Section -->
    <view class="result-section" v-if="generatedStructures.length > 0">
      <view class="result-header">
        <text class="result-title">生成结果</text>
        <text class="result-count">{{ generatedStructures.length }} 个结构</text>
      </view>

      <view class="structures-list">
        <view class="structure-card" v-for="(structure, index) in generatedStructures" :key="index">
          <view class="structure-header">
            <text class="structure-formula">{{ structure.formula }}</text>
            <text class="structure-bandgap">{{ structure.predicted_bandgap.toFixed(2) }} eV</text>
          </view>

          <view class="halogen-composition">
            <view class="halogen-item">
              <text class="halogen-label cl-color">Cl</text>
              <text class="halogen-value">{{ structure.cl_ratio.toFixed(2) }}</text>
            </view>
            <view class="halogen-item">
              <text class="halogen-label br-color">Br</text>
              <text class="halogen-value">{{ structure.br_ratio.toFixed(2) }}</text>
            </view>
            <view class="halogen-item">
              <text class="halogen-label i-color">I</text>
              <text class="halogen-value">{{ structure.i_ratio.toFixed(2) }}</text>
            </view>
          </view>

          <view class="structure-actions">
            <button class="action-btn predict-btn" @click="predictStructure(structure)">
              <text class="action-text">详细预测</text>
            </button>
            <button class="action-btn analyze-btn" @click="analyzeStructure(structure)">
              <text class="action-text">分析</text>
            </button>
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
      targetBandgap: 1.8,
      nSamples: 5,
      bandgapTolerance: 0.3,
      toleranceOptions: [0.1, 0.2, 0.3, 0.5],
      isLoading: false,
      generatedStructures: []
    }
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

    onBandgapChange(e) {
      this.targetBandgap = e.detail.value / 100
    },

    onBandgapInput(e) {
      const value = parseFloat(e.detail.value)
      if (!isNaN(value)) {
        this.targetBandgap = Math.max(1.0, Math.min(3.0, value))
      }
    },

    decreaseSamples() {
      if (this.nSamples > 1) {
        this.nSamples--
      }
    },

    increaseSamples() {
      if (this.nSamples < 20) {
        this.nSamples++
      }
    },

    selectTolerance(tolerance) {
      this.bandgapTolerance = tolerance
    },

    async generate() {
      if (this.isLoading) return

      this.isLoading = true

      try {
        const response = await api.generateStructures({
          a_site: this.selectedA,
          b_site: this.selectedB,
          target_bandgap: this.targetBandgap,
          n_samples: this.nSamples,
          bandgap_tolerance: this.bandgapTolerance
        })

        this.generatedStructures = response.generated_structures

      } catch (error) {
        console.error('生成失败:', error)
        // 使用模拟数据
        this.simulateGeneration()
      }

      this.isLoading = false
    },

    simulateGeneration() {
      // 模拟生成结果
      const structures = []
      for (let i = 0; i < this.nSamples; i++) {
        const cl = Math.random() * 1.5
        const br = Math.random() * (1.5 - cl)
        const i = 3 - cl - br
        
        // 计算模拟带隙
        const baseBandgap = {
          'Cl': 3.26, 'Br': 2.81, 'I': 2.37
        }
        const bandgap = (cl * baseBandgap.Cl + br * baseBandgap.Br + i * baseBandgap.I) / 3
        
        // 添加一些随机性
        const noise = (Math.random() - 0.5) * 0.2
        const finalBandgap = bandgap + noise

        structures.push({
          formula: `${this.selectedA}${this.selectedB}Cl_${cl.toFixed(2)}Br_${br.toFixed(2)}I_${i.toFixed(2)}`,
          predicted_bandgap: finalBandgap,
          cl_ratio: cl,
          br_ratio: br,
          i_ratio: i
        })
      }

      // 按带隙接近目标值排序
      structures.sort((a, b) => {
        return Math.abs(a.predicted_bandgap - this.targetBandgap) - Math.abs(b.predicted_bandgap - this.targetBandgap)
      })

      this.generatedStructures = structures
    },

    predictStructure(structure) {
      // 跳转到预测页面并传递参数
      uni.navigateTo({
        url: `/pages/prediction/prediction?a_site=${this.selectedA}&b_site=${this.selectedB}&cl_ratio=${structure.cl_ratio}&br_ratio=${structure.br_ratio}&i_ratio=${structure.i_ratio}`
      })
    },

    analyzeStructure(structure) {
      // 跳转到分析页面并传递参数
      uni.navigateTo({
        url: `/pages/analysis/analysis?formula=${structure.formula}&bandgap=${structure.predicted_bandgap}`
      })
    }
  },

  onLoad() {
    this.loadElements()
  }
}
</script>

<style scoped>
.generator-container {
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
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
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
  background: linear-gradient(90deg, #8b5cf6, #d946ef);
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

/* Slider with Input */
.slider-with-input {
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.slider-with-input slider {
  flex: 1;
}

.bandgap-input {
  width: 120rpx;
  height: 60rpx;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12rpx;
  color: #f9fafb;
  font-size: 24rpx;
  text-align: center;
}

/* Number Input */
.number-input {
  display: flex;
  align-items: center;
  gap: 20rpx;
  width: 240rpx;
}

.number-btn {
  width: 60rpx;
  height: 60rpx;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12rpx;
  font-size: 32rpx;
  color: #f9fafb;
}

.number-btn[disabled] {
  opacity: 0.5;
}

.number-value {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
  min-width: 60rpx;
  text-align: center;
}

/* Tolerance Options */
.tolerance-options {
  display: flex;
  gap: 16rpx;
}

.tolerance-option {
  flex: 1;
  background: #1f2937;
  border: 2px solid #374151;
  border-radius: 12rpx;
  padding: 16rpx;
  text-align: center;
  transition: all 0.3s ease;
}

.tolerance-option.active {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  border-color: #8b5cf6;
}

.tolerance-text {
  font-size: 24rpx;
  font-weight: 500;
  color: #f9fafb;
}

/* Generate Button */
.generate-btn {
  width: 100%;
  height: 96rpx;
  background: linear-gradient(135deg, #8b5cf6, #d946ef);
  border: none;
  border-radius: 24rpx;
  margin-top: 16rpx;
}

.generate-btn[disabled] {
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

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.result-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #f9fafb;
}

.result-count {
  font-size: 24rpx;
  color: #6b7280;
  background: #1f2937;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
}

/* Structures List */
.structures-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.structure-card {
  background: #111827;
  border-radius: 20rpx;
  padding: 24rpx;
  border: 1px solid #374151;
  transition: all 0.3s ease;
}

.structure-card:hover {
  border-color: #8b5cf6;
  box-shadow: 0 4rpx 20rpx rgba(139, 92, 246, 0.1);
}

.structure-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.structure-formula {
  font-size: 24rpx;
  font-family: 'Courier New', monospace;
  color: #00d4ff;
  font-weight: 500;
}

.structure-bandgap {
  font-size: 24rpx;
  font-weight: 600;
  color: #8b5cf6;
  background: #1f2937;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
}

/* Halogen Composition */
.halogen-composition {
  display: flex;
  gap: 20rpx;
  margin-bottom: 20rpx;
  padding: 16rpx;
  background: #1a1f2e;
  border-radius: 12rpx;
}

.halogen-item {
  flex: 1;
  text-align: center;
}

.halogen-label {
  font-size: 22rpx;
  font-weight: 500;
  display: block;
  margin-bottom: 4rpx;
}

.cl-color { color: #00d4ff; }
.br-color { color: #8b5cf6; }
.i-color { color: #10b981; }

.halogen-value {
  font-size: 24rpx;
  color: #f9fafb;
  font-weight: 600;
}

/* Structure Actions */
.structure-actions {
  display: flex;
  gap: 12rpx;
}

.action-btn {
  flex: 1;
  height: 64rpx;
  border-radius: 12rpx;
  border: none;
  font-size: 22rpx;
  font-weight: 500;
}

.predict-btn {
  background: linear-gradient(135deg, #00d4ff, #0099cc);
}

.analyze-btn {
  background: linear-gradient(135deg, #10b981, #059669);
}

.action-text {
  color: #ffffff;
}
</style>