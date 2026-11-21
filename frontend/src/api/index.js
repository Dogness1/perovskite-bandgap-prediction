/**
 * API 工具模块
 * 封装所有后端API调用
 */

/**
 * 通用请求方法
 */
const request = (options) => {
  return new Promise((resolve, reject) => {
    fetch(options.url, {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.header
      },
      body: options.data ? JSON.stringify(options.data) : undefined
    })
      .then(res => {
        if (res.ok) {
          if (options.responseType === 'blob') {
            return res.blob()
          }
          return res.json()
        }
        throw new Error(`请求失败: ${res.status}`)
      })
      .then(data => {
        resolve(data)
      })
      .catch(err => {
        console.error('API请求失败:', err)
        reject(err)
      })
  })
}

/**
 * API 接口定义
 */
export const api = {
  // 健康检查
  healthCheck() {
    return request({ url: '/api/health' })
  },

  // 获取数据集统计信息
  getDataStats() {
    return request({ url: '/api/data/stats' })
  },

  // 获取数据分布信息
  getDataDistribution() {
    return request({ url: '/api/data/distribution' })
  },

  // 带隙预测
  predictBandgap(data) {
    return request({
      url: '/api/predict',
      method: 'POST',
      data
    })
  },

  // 生成新结构
  generateStructures(data) {
    return request({
      url: '/api/generate',
      method: 'POST',
      data
    })
  },

  // 分析结构对比
  analyzeStructure(data) {
    return request({
      url: '/api/analyze',
      method: 'POST',
      data
    })
  },

  // 获取卤素影响分析
  getHalogenEffect() {
    return request({ url: '/api/halogen-effect' })
  },

  // 获取特征重要性
  getFeatureImportance() {
    return request({ url: '/api/feature-importance' })
  },

  // 获取可用元素列表
  getElements() {
    return request({ url: '/api/elements' })
  },

  // 获取结构描述子默认值（高级选项）
  getStructureDefaults() {
    return request({ url: '/api/structure-defaults' })
  },

  // 导出数据
  exportData(format) {
    return request({
      url: `/api/data/export?format=${format}`,
      responseType: 'blob'
    })
  },

  // 批量预测
  batchPredict(structures) {
    return request({
      url: '/api/predict/batch',
      method: 'POST',
      data: { structures }
    })
  }
}

export default api
