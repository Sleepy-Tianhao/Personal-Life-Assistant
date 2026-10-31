import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '今日' },
  },
  {
    path: '/todos',
    name: 'todos',
    component: () => import('@/views/TodosView.vue'),
    meta: { title: '待办' },
  },
  {
    path: '/schedule',
    name: 'schedule',
    component: () => import('@/views/ScheduleView.vue'),
    meta: { title: '日程' },
  },
  {
    path: '/timetable',
    name: 'timetable',
    component: () => import('@/views/TimetableView.vue'),
    meta: { title: '课表' },
  },
  {
    path: '/ledger',
    name: 'ledger',
    component: () => import('@/views/LedgerView.vue'),
    meta: { title: '账本' },
  },
  {
    path: '/diary',
    name: 'diary',
    component: () => import('@/views/DiaryView.vue'),
    meta: { title: '日记' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Life Assistant` : 'Life Assistant'
})

export default router
