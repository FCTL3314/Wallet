<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}>(), {
  variant: 'secondary',
  size: 'md',
  type: 'button',
})
</script>

<template>
  <button :type="type" :disabled="disabled" :class="['btn', `btn-${variant}`, { 'btn-sm': size === 'sm' }]">
    <slot />
  </button>
</template>
