<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  tone: { type: String, default: 'accent' },
})
</script>

<template>
  <article class="metric-card card" :class="`metric-card--${tone}`">
    <div class="metric-top">
      <span class="metric-label">{{ label }}</span>
      <span v-if="icon" class="metric-icon">
        <component :is="icon" :size="17" :stroke-width="1.8" />
      </span>
    </div>
    <strong class="metric-value">{{ value }}</strong>
    <span v-if="hint" class="metric-hint">{{ hint }}</span>
    <slot />
  </article>
</template>

<style scoped>
.metric-card {
  position: relative;
  min-height: 124px;
  padding: 16px 18px;
  overflow: hidden;
}

.metric-card--income {
  --metric-color: var(--income);
  --metric-bg: var(--success-soft);
}

.metric-card--expense {
  --metric-color: var(--expense);
  --metric-bg: var(--danger-soft);
}

.metric-card--warning {
  --metric-color: var(--warning);
  --metric-bg: var(--warning-soft);
}

.metric-card--accent {
  --metric-color: var(--accent-deep);
  --metric-bg: var(--accent-soft);
}

.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.metric-label {
  color: var(--text-3);
  font-size: 10.5px;
  font-weight: 620;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.metric-icon {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--metric-color, var(--accent)) 14%, white);
  border-radius: 9px;
  color: var(--metric-color, var(--accent));
  background: var(--metric-bg, var(--accent-soft));
}

.metric-value {
  display: block;
  margin-top: 13px;
  color: var(--text-1);
  font-family: var(--font-display);
  font-size: 25px;
  font-weight: 660;
  letter-spacing: -0.04em;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.metric-hint {
  display: block;
  margin-top: 6px;
  color: var(--text-3);
  font-size: 10.5px;
}
</style>
