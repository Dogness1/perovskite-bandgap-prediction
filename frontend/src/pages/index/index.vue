<template>
  <div class="dashboard-container page-container">
    <!-- Crystal Lattice Background -->
    <div class="crystal-bg"></div>

    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1 class="title glow-text">钙钛矿研究平台</h1>
        <p class="subtitle">Perovskite Band Gap Prediction System</p>
      </div>
      <div class="header-decoration">
        <div class="crystal-icon">
          <div class="crystal-shape"></div>
        </div>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card" v-for="(stat, index) in statsCards" :key="index">
        <div class="stat-icon" :style="{ background: stat.gradient }">
          <span class="icon-text">{{ stat.icon }}</span>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>
    </div>

    <!-- Halogen Distribution Chart -->
    <div class="chart-section">
      <div class="section-header">
        <h2 class="section-title">卤素分布</h2>
        <p class="section-subtitle">Halogen Distribution</p>
      </div>
      <div class="chart-container">
        <div class="pie-chart">
          <div class="pie-center">
            <span class="pie-total">{{ totalSamples }}</span>
            <span class="pie-label">样本总数</span>
          </div>
          <div class="pie-segments" :style="pieStyle"></div>
        </div>
        <div class="pie-legend">
          <div class="legend-item" v-for="(item, index) in halogenData" :key="index">
            <div class="legend-color" :style="{ background: item.color }"></div>
            <span class="legend-text">{{ item.name }}</span>
            <span class="legend-value">{{ item.count }}</span>
            <span class="legend-percent">{{ item.percent }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Band Gap Distribution -->
    <div class="chart-section">
      <div class="section-header">
        <h2 class="section-title">带隙分布</h2>
        <p class="section-subtitle">Band Gap Distribution (eV)</p>
      </div>
      <div class="histogram-container">
        <div class="histogram-bars">
          <div
            class="histogram-bar"
            v-for="(bar, index) in histogramData"
            :key="index"
            :style="{ height: bar.height + '%', background: bar.color }"
          >
            <span class="bar-value" v-if="bar.count > 0">{{ bar.count }}</span>
          </div>
        </div>
        <div class="histogram-labels">
          <span class="label-item" v-for="(label, index) in histogramLabels" :key="index">
            {{ label }}
          </span>
        </div>
      </div>
    </div>

    <!-- Band Gap by Halogen -->
    <div class="chart-section">
      <div class="section-header">
        <h2 class="section-title">卤素-带隙关系</h2>
        <p class="section-subtitle">Halogen vs Band Gap</p>
      </div>
      <div class="halogen-stats">
        <div class="halogen-card" v-for="(item, index) in halogenBandgapStats" :key="index">
          <div class="halogen-header" :style="{ borderBottomColor: item.color }">
            <span class="halogen-symbol" :style="{ color: item.color }">{{ item.symbol }}</span>
            <span class="halogen-name">{{ item.name }}</span>
          </div>
          <div class="halogen-metrics">
            <div class="metric">
              <span class="metric-value">{{ item.mean }}</span>
              <span class="metric-label">平均带隙 (eV)</span>
            </div>
            <div class="metric">
              <span class="metric-value">{{ item.range }}</span>
              <span class="metric-label">范围 (eV)</span>
            </div>
          </div>
          <div class="bandgap-bar-container">
            <div class="bandgap-bar" :style="{ width: item.barWidth + '%', background: item.color }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Samples -->
    <div class="chart-section">
      <div class="section-header">
        <h2 class="section-title">样本示例</h2>
        <p class="section-subtitle">Sample Formulas</p>
      </div>
      <div class="sample-list">
        <div class="sample-item" v-for="(formula, index) in sampleFormulas" :key="index">
          <span class="sample-formula">{{ formatFormula(formula) }}</span>
          <div class="sample-index">{{ index + 1 }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '../../api/index.js'

export default {
  data() {
    return {
      statsCards: [
        { icon: '📊', label: '样本总数', value: '加载中...', gradient: 'linear-gradient(135deg, #00d4ff, #0099cc)' },
        { icon: '⚡', label: '平均带隙', value: '加载中...', gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' },
        { icon: '🔬', label: 'A位元素', value: '加载中...', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
        { icon: '🧪', label: 'B位元素', value: '加载中...', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' }
      ],
      halogenData: [
        { name: 'Cl (氯)', symbol: 'Cl', count: 127, percent: 26, color: '#00d4ff' },
        { name: 'Br (溴)', symbol: 'Br', count: 163, percent: 33, color: '#8b5cf6' },
        { name: 'I (碘)', symbol: 'I', count: 198, percent: 41, color: '#10b981' }
      ],
      totalSamples: 488,
      histogramData: [],
      histogramLabels: ['0-1', '1-2', '2-3', '3-4', '4-5', '5-6'],
      halogenBandgapStats: [],
      sampleFormulas: [],
      pieStyle: ''
    }
  },

  mounted() {
    this.loadData()
  },

  methods: {
    async loadData() {
      try {
        // 获取数据统计
        const stats = await api.getDataStats()
        this.updateStats(stats)

        // 获取数据分布
        const distribution = await api.getDataDistribution()
        this.updateDistribution(distribution)

      } catch (error) {
        console.error('加载数据失败:', error)
        // 使用模拟数据
        this.loadMockData()
      }
    },

    updateStats(stats) {
      this.totalSamples = stats.total_samples
      this.statsCards = [
        {
          icon: '📊',
          label: '样本总数',
          value: stats.total_samples,
          gradient: 'linear-gradient(135deg, #00d4ff, #0099cc)'
        },
        {
          icon: '⚡',
          label: '平均带隙',
          value: stats.bandgap_range.mean.toFixed(2) + ' eV',
          gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)'
        },
        {
          icon: '🔬',
          label: 'A位元素',
          value: stats.elements?.A_sites?.length || 6,
          gradient: 'linear-gradient(135deg, #10b981, #059669)'
        },
        {
          icon: '🧪',
          label: 'B位元素',
          value: stats.elements?.B_sites?.length || 14,
          gradient: 'linear-gradient(135deg, #f59e0b, #d97706)'
        }
      ]
      this.sampleFormulas = stats.sample_formulas?.slice(0, 10) || []
    },

    updateDistribution(distribution) {
      // 更新卤素分布
      const halogenDist = distribution.halogen_distribution
      const total = Object.values(halogenDist).reduce((a, b) => a + b, 0)

      this.halogenData = [
        {
          name: 'Cl (氯)',
          symbol: 'Cl',
          count: halogenDist.Cl || 127,
          percent: Math.round((halogenDist.Cl || 127) / total * 100),
          color: '#00d4ff'
        },
        {
          name: 'Br (溴)',
          symbol: 'Br',
          count: halogenDist.Br || 163,
          percent: Math.round((halogenDist.Br || 163) / total * 100),
          color: '#8b5cf6'
        },
        {
          name: 'I (碘)',
          symbol: 'I',
          count: halogenDist.I || 198,
          percent: Math.round((halogenDist.I || 198) / total * 100),
          color: '#10b981'
        }
      ]

      // 更新直方图
      const histData = distribution.bandgap_histogram
      if (histData) {
        const maxCount = Math.max(...histData.counts)
        this.histogramData = histData.counts.map((count, index) => ({
          count,
          height: maxCount > 0 ? (count / maxCount * 100) : 0,
          color: this.getHistogramColor(index)
        }))
      }

      // 更新卤素带隙统计
      const halogenStats = distribution.halogen_bandgap_stats
      if (halogenStats) {
        this.halogenBandgapStats = [
          {
            symbol: 'Cl',
            name: '氯',
            mean: halogenStats.Cl?.mean.toFixed(2) || '3.26',
            range: `${halogenStats.Cl?.min.toFixed(1) || '0.9'}-${halogenStats.Cl?.max.toFixed(1) || '5.4'}`,
            color: '#00d4ff',
            barWidth: 70
          },
          {
            symbol: 'Br',
            name: '溴',
            mean: halogenStats.Br?.mean.toFixed(2) || '2.81',
            range: `${halogenStats.Br?.min.toFixed(1) || '0.5'}-${halogenStats.Br?.max.toFixed(1) || '4.9'}`,
            color: '#8b5cf6',
            barWidth: 60
          },
          {
            symbol: 'I',
            name: '碘',
            mean: halogenStats.I?.mean.toFixed(2) || '2.37',
            range: `${halogenStats.I?.min.toFixed(1) || '0.4'}-${halogenStats.I?.max.toFixed(1) || '4.6'}`,
            color: '#10b981',
            barWidth: 50
          }
        ]
      }
    },

    getHistogramColor(index) {
      const colors = [
        'linear-gradient(180deg, #10b981, #059669)',
        'linear-gradient(180deg, #00d4ff, #0099cc)',
        'linear-gradient(180deg, #8b5cf6, #6d28d9)',
        'linear-gradient(180deg, #f59e0b, #d97706)',
        'linear-gradient(180deg, #f43f5e, #dc2626)',
        'linear-gradient(180deg, #ec4899, #be185d)'
      ]
      return colors[index] || colors[0]
    },

    formatFormula(formula) {
      return formula?.replace(/_/g, '₋') || formula
    },

    loadMockData() {
      this.histogramData = [
        { count: 45, height: 45, color: this.getHistogramColor(0) },
        { count: 120, height: 100, color: this.getHistogramColor(1) },
        { count: 98, height: 82, color: this.getHistogramColor(2) },
        { count: 75, height: 63, color: this.getHistogramColor(3) },
        { count: 52, height: 43, color: this.getHistogramColor(4) },
        { count: 18, height: 15, color: this.getHistogramColor(5) }
      ]

      this.halogenBandgapStats = [
        { symbol: 'Cl', name: '氯', mean: '3.26', range: '0.9-5.4', color: '#00d4ff', barWidth: 70 },
        { symbol: 'Br', name: '溴', mean: '2.81', range: '0.5-4.9', color: '#8b5cf6', barWidth: 60 },
        { symbol: 'I', name: '碘', mean: '2.37', range: '0.4-4.6', color: '#10b981', barWidth: 50 }
      ]

      this.sampleFormulas = [
        'CsPbI_3', 'MAPbBr_3', 'FAGeCl_3', 'CsSnI_2.25Br_0.75',
        'RbPbBr_1.5Cl_1.5', 'MASnI_3', 'CsGeBr_3', 'FAPbI_3',
        'KPbCl_3', 'RbSnBr_3'
      ]
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  padding: 16px;
  padding-bottom: 70px;
  position: relative;
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-radius: 12px;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #f9fafb;
  display: block;
}

.subtitle {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
  display: block;
}

.crystal-icon {
  width: 40px;
  height: 40px;
  position: relative;
}

.crystal-shape {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #00d4ff, #8b5cf6);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: #111827;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #374151;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: scale(0.98);
  border-color: rgba(0, 212, 255, 0.5);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-text {
  font-size: 18px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #f9fafb;
  display: block;
}

.stat-label {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
  display: block;
}

/* Chart Sections */
.chart-section {
  background: #111827;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #374151;
  position: relative;
  overflow: hidden;
}

.chart-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6, #10b981);
}

.section-header {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #f9fafb;
  display: block;
}

.section-subtitle {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
  display: block;
}

/* Pie Chart */
.chart-container {
  display: flex;
  align-items: center;
  gap: 20px;
}

.pie-chart {
  width: 120px;
  height: 120px;
  position: relative;
  flex-shrink: 0;
}

.pie-segments {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: conic-gradient(
    #00d4ff 0deg 94deg,
    #8b5cf6 94deg 212deg,
    #10b981 212deg 360deg
  );
}

.pie-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 60px;
  height: 60px;
  background: #111827;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pie-total {
  font-size: 18px;
  font-weight: 700;
  color: #f9fafb;
}

.pie-label {
  font-size: 9px;
  color: #9ca3af;
}

.pie-legend {
  flex: 1;
}

.legend-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #1f2937;
}

.legend-item:last-child {
  border-bottom: none;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  margin-right: 8px;
}

.legend-text {
  flex: 1;
  font-size: 13px;
  color: #f9fafb;
}

.legend-value {
  font-size: 13px;
  color: #9ca3af;
  margin-right: 8px;
}

.legend-percent {
  font-size: 12px;
  color: #6b7280;
  width: 30px;
  text-align: right;
}

/* Histogram */
.histogram-container {
  padding: 10px 0;
}

.histogram-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 150px;
  gap: 6px;
  padding-bottom: 8px;
}

.histogram-bar {
  flex: 1;
  border-radius: 4px 4px 0 0;
  min-height: 10px;
  position: relative;
  transition: all 0.3s ease;
}

.histogram-bar:hover {
  transform: scaleY(1.05);
}

.bar-value {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: #f9fafb;
  background: rgba(0, 0, 0, 0.6);
  padding: 2px 6px;
  border-radius: 4px;
}

.histogram-labels {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
}

.label-item {
  flex: 1;
  text-align: center;
  font-size: 10px;
  color: #6b7280;
}

/* Halogen Stats */
.halogen-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.halogen-card {
  background: #1a1f2e;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #374151;
}

.halogen-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 2px solid;
  margin-bottom: 8px;
}

.halogen-symbol {
  font-size: 18px;
  font-weight: 700;
}

.halogen-name {
  font-size: 13px;
  color: #9ca3af;
}

.halogen-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 8px;
}

.metric {
  flex: 1;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #f9fafb;
  display: block;
}

.metric-label {
  font-size: 10px;
  color: #6b7280;
  margin-top: 2px;
  display: block;
}

.bandgap-bar-container {
  height: 6px;
  background: #1f2937;
  border-radius: 3px;
  overflow: hidden;
}

.bandgap-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

/* Sample List */
.sample-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sample-item {
  background: #1a1f2e;
  border-radius: 6px;
  padding: 8px 12px;
  border: 1px solid #374151;
  position: relative;
  overflow: hidden;
}

.sample-formula {
  font-size: 12px;
  color: #f9fafb;
  font-family: 'Courier New', monospace;
}

.sample-index {
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 8px;
  color: #4b5563;
}
</style>
