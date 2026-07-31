<script setup lang="ts">
const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  loading?: boolean
}>(), {
  variant: 'secondary',
  size: 'md',
  type: 'button',
  disabled: false,
  loading: false,
})
</script>

<template>
  <button
    :type="type"
    :disabled="props.disabled || props.loading"
    :aria-busy="props.loading"
    :class="['btn', `btn-${props.variant}`, { 'btn-sm': props.size === 'sm', 'btn-loading': props.loading }]"
  >
    <slot />
    <span v-if="props.loading" class="btn-spinner" aria-hidden="true" />
  </button>
</template>
