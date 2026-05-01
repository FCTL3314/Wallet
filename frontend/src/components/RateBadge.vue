<script setup lang="ts">
import { computed } from 'vue'
import { PhCheck, PhInfo, PhArrowsClockwise } from '@phosphor-icons/vue'

const props = defineProps<{
  asOf: string | null
  refreshable?: boolean
}>()

const emit = defineEmits<{ refresh: [] }>()

const days = computed(() => {
  if (!props.asOf) return null
  const a = new Date(props.asOf)
  const t = new Date()
  return Math.round((t.getTime() - a.getTime()) / 86400000)
})

const stale = computed(() => days.value !== null && days.value >= 2)
</script>

<template>
  <span class="rate-badge" :class="{ 'rate-badge--stale': stale }" title="Currency rates freshness">
    <PhInfo v-if="stale" :size="13" weight="bold" />
    <PhCheck v-else :size="13" weight="bold" />
    <span v-if="asOf">Rates · {{ asOf }}<template v-if="stale && days !== null"> · {{ days }}d old</template></span>
    <span v-else>Rates · n/a</span>
    <button
      v-if="refreshable"
      class="rate-refresh"
      type="button"
      title="Refresh"
      @click.stop="emit('refresh')"
    ><PhArrowsClockwise :size="11" weight="bold" /></button>
  </span>
</template>

<style scoped>
.rate-refresh {
  margin-left: 2px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: inherit;
  cursor: pointer;
}
.rate-refresh:hover { background: rgba(0,0,0,0.06); }
[data-theme="dark"] .rate-refresh:hover { background: rgba(255,255,255,0.08); }
</style>
