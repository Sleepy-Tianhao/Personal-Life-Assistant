<script setup>
import { Sparkles } from '@lucide/vue'

defineProps({
  title: { type: String, default: '这里还是空的' },
  description: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
})
</script>

<template>
  <div class="empty-state">
    <span class="empty-state__icon">
      <component :is="icon || Sparkles" :size="20" />
    </span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <slot />
  </div>
</template>
