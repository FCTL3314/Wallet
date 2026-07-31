<script setup lang="ts">
import { useRoute } from 'vue-router'
import { PhCompass, PhArrowLeft } from '@phosphor-icons/vue'
import { DEFAULT_ROUTE } from '../router'

const route = useRoute()
</script>

<template>
  <div class="page-sections">
    <div class="card not-found">
      <span class="not-found-mark" aria-hidden="true">
        <PhCompass weight="duotone" :size="30" />
      </span>
      <p class="not-found-code">404</p>
      <p class="not-found-text">
        We could not find a page at
        <span class="not-found-path">{{ route.fullPath }}</span>
      </p>
      <p class="not-found-hint">The link may be outdated, or the address may contain a typo.</p>
      <RouterLink :to="DEFAULT_ROUTE" class="btn btn--primary">
        <PhArrowLeft weight="bold" :size="16" />
        Back to dashboard
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  padding: 48px 24px;
}

.not-found-mark {
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  border-radius: var(--r-pill);
  background: var(--accent-soft);
  color: var(--accent-ink);
  margin-bottom: 6px;
}

.not-found-code {
  font-family: var(--font-display);
  font-size: 40px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--ink);
  line-height: 1;
}

.not-found-text {
  font-size: 15px;
  color: var(--ink-2);
  max-width: 46ch;
}

.not-found-path {
  font-family: var(--font-mono);
  font-size: 13px;
  padding: 2px 6px;
  border-radius: var(--r-chip);
  background: var(--surface-2);
  color: var(--ink);
  overflow-wrap: anywhere;
}

.not-found-hint {
  font-size: 13px;
  color: var(--ink-3);
  margin-bottom: 12px;
  max-width: 46ch;
}
</style>
