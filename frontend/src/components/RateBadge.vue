<script setup lang="ts">
import { computed } from 'vue'
import { PhCheck, PhInfo } from '@phosphor-icons/vue'

const props = defineProps<{
  asOf: string | null
}>()

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
  </span>
</template>
