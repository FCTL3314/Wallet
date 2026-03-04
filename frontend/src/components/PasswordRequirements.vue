<script setup lang="ts">
defineProps<{ password: string }>()

const checks = [
  { label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { label: 'Uppercase letter (A–Z)', test: (p: string) => /[A-Z]/.test(p) },
  { label: 'Lowercase letter (a–z)', test: (p: string) => /[a-z]/.test(p) },
  { label: 'At least one digit (0–9)', test: (p: string) => /\d/.test(p) },
]
</script>

<template>
  <div class="password-requirements" v-if="password">
    <div
      v-for="check in checks"
      :key="check.label"
      :class="['req-item', check.test(password) ? 'req-met' : 'req-unmet']"
    >
      <span class="req-icon">{{ check.test(password) ? '✓' : '✗' }}</span>
      {{ check.label }}
    </div>
  </div>
</template>
