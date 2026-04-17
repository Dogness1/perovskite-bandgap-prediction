<template>
  <div id="app">
    <div class="app-container">
      <router-view />
      <!-- Bottom Navigation -->
      <nav class="bottom-nav">
        <router-link to="/" class="nav-item" active-class="active">
          <span class="nav-icon">🏠</span>
          <span class="nav-text">首页</span>
        </router-link>
        <router-link to="/prediction" class="nav-item" active-class="active">
          <span class="nav-icon">🔮</span>
          <span class="nav-text">预测</span>
        </router-link>
        <router-link to="/generator" class="nav-item" active-class="active">
          <span class="nav-icon">⚡</span>
          <span class="nav-text">生成</span>
        </router-link>
        <router-link to="/analysis" class="nav-item" active-class="active">
          <span class="nav-icon">📊</span>
          <span class="nav-text">分析</span>
        </router-link>
      </nav>
    </div>
  </div>
</template>

<script>
export default {
  onLaunch() {
    console.log('Perovskite Band Gap Prediction System Launched')
  },
  onShow() {
    console.log('App Show')
  },
  onHide() {
    console.log('App Hide')
  }
}
</script>

<style>
/* Global Styles - Quantum Lab Theme */
:root {
  --primary-cyan: #00d4ff;
  --primary-purple: #8b5cf6;
  --primary-emerald: #10b981;
  --primary-amber: #f59e0b;
  --primary-rose: #f43f5e;

  --bg-deep: #0a0e17;
  --bg-card: #111827;
  --bg-card-hover: #1f2937;
  --bg-input: #1a1f2e;

  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;

  --border-color: #374151;
  --border-glow: rgba(0, 212, 255, 0.3);
}

page {
  background-color: var(--bg-deep);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  min-height: 100vh;
}

.app-container {
  background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #0f172a 100%);
  min-height: 100vh;
}

/* Crystal lattice background pattern */
.crystal-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* Glowing text effect */
.glow-text {
  text-shadow: 0 0 10px var(--primary-cyan), 0 0 20px var(--primary-cyan);
}

/* Card styles */
.quantum-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24rpx;
  margin: 20rpx;
  position: relative;
  overflow: hidden;
}

.quantum-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary-cyan), var(--primary-purple), var(--primary-emerald));
}

/* Button styles */
.btn-primary {
  background: linear-gradient(135deg, var(--primary-cyan), var(--primary-purple));
  color: white;
  border: none;
  border-radius: 12rpx;
  padding: 24rpx 48rpx;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-primary:active {
  transform: scale(0.98);
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
}

/* Input styles */
.quantum-input {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 12rpx;
  padding: 24rpx 32rpx;
  color: var(--text-primary);
  font-size: 28rpx;
}

.quantum-input:focus {
  border-color: var(--primary-cyan);
  box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
}

/* Bottom Navigation */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 100rpx;
  z-index: 1000;
  backdrop-filter: blur(10px);
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.3);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.3s ease;
}

.nav-item:hover {
  color: var(--primary-cyan);
}

.nav-item.active {
  color: var(--primary-cyan);
  background: linear-gradient(to top, rgba(0, 212, 255, 0.1), transparent);
}

.nav-icon {
  font-size: 32rpx;
  margin-bottom: 4rpx;
}

.nav-text {
  font-size: 20rpx;
  font-weight: 500;
}

/* Page container padding to avoid bottom nav overlap */
.page-container {
  padding-bottom: 120rpx;
}
</style>
