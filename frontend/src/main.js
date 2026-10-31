import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/base.css'
import { applyAccent, getStoredAccent } from './utils/theme'

applyAccent(getStoredAccent())

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
