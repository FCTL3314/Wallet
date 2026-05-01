<script setup lang="ts">
import { computed } from 'vue'
import { PhCaretUp, PhCaretDown } from '@phosphor-icons/vue'

const props = withDefaults(
  defineProps<{
    delta: number
    showIcon?: boolean
  }>(),
  { showIcon: true },
)

const cls = computed(() =>
  props.delta > 0 ? 'growth--up' : props.delta < 0 ? 'growth--down' : 'growth--flat',
)
</script>

<template>
  <span class="growth" :class="cls">
    <template v-if="showIcon">
      <PhCaretUp v-if="delta >= 0" :size="11" weight="bold" />
      <PhCaretDown v-else :size="11" weight="bold" />
    </template>
    <slot />
  </span>
</template>
