import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../pages/index/index.vue')
  },
  {
    path: '/prediction',
    name: 'Prediction',
    component: () => import('../pages/prediction/prediction.vue')
  },
  {
    path: '/generator',
    name: 'Generator',
    component: () => import('../pages/generator/generator.vue')
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('../pages/analysis/analysis.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router