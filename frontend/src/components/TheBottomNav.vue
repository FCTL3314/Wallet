<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { PhDotsThreeOutline } from '@phosphor-icons/vue'
import { PRIMARY_NAV_ITEMS, SECONDARY_NAV_ITEMS } from '../router'

const route = useRoute()
const sheetOpen = ref(false)
const sheetTrigger = useTemplateRef<HTMLButtonElement>('sheetTrigger')
const sheetPanel = useTemplateRef<HTMLElement>('sheetPanel')

const moreActive = computed(() => SECONDARY_NAV_ITEMS.some((item) => item.path === route.path))

function openSheet() {
  sheetOpen.value = true
}

function closeSheet(restoreFocus = false) {
  if (!sheetOpen.value) return
  sheetOpen.value = false
  if (restoreFocus) sheetTrigger.value?.focus()
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeSheet(true)
}

function trapTab(event: KeyboardEvent) {
  const items = Array.from(sheetPanel.value?.querySelectorAll<HTMLElement>('.sheet-item') ?? [])
  if (!items.length) return
  const current = items.indexOf(document.activeElement as HTMLElement)
  const offset = event.shiftKey ? -1 : 1
  items[(current + offset + items.length) % items.length]?.focus()
}

watch(sheetOpen, async (open) => {
  if (open) {
    document.addEventListener('keydown', onDocumentKeydown)
    await nextTick()
    sheetPanel.value?.querySelector<HTMLElement>('.sheet-item')?.focus()
  } else {
    document.removeEventListener('keydown', onDocumentKeydown)
  }
})

watch(() => route.fullPath, () => closeSheet())

onBeforeUnmount(() => document.removeEventListener('keydown', onDocumentKeydown))
</script>

<template>
  <nav class="bottom-nav" aria-label="Primary navigation">
    <RouterLink
      v-for="item in PRIMARY_NAV_ITEMS"
      :key="item.path"
      :to="item.path"
      class="bottom-nav-item"
      :aria-label="item.label"
    >
      <component :is="item.icon" weight="duotone" :size="22" />
      <span>{{ item.shortLabel }}</span>
    </RouterLink>
    <button
      ref="sheetTrigger"
      type="button"
      class="bottom-nav-item"
      :class="{ 'bottom-nav-item--active': moreActive }"
      aria-haspopup="dialog"
      aria-controls="more-sheet"
      :aria-expanded="sheetOpen"
      aria-label="More sections"
      @click="openSheet"
    >
      <PhDotsThreeOutline weight="duotone" :size="22" />
      <span>More</span>
    </button>
  </nav>

  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="sheetOpen" class="sheet-overlay" @click.self="closeSheet()">
        <div
          id="more-sheet"
          ref="sheetPanel"
          class="sheet"
          role="dialog"
          aria-modal="true"
          aria-labelledby="more-sheet-title"
          @keydown.tab.prevent="trapTab"
        >
          <span class="sheet-grip" aria-hidden="true" />
          <h2 id="more-sheet-title" class="sheet-title">More</h2>
          <RouterLink
            v-for="item in SECONDARY_NAV_ITEMS"
            :key="item.path"
            :to="item.path"
            class="sheet-item"
            @click="closeSheet()"
          >
            <component :is="item.icon" weight="duotone" :size="20" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.bottom-nav {
  display: none;
}

@media (max-width: 640px) {
  .bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: var(--surface);
    border-top: 1px solid var(--hairline);
    border-radius: 20px 20px 0 0;
    box-shadow: 0 -2px 12px rgba(24, 20, 10, 0.08);
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
}

.bottom-nav-item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: var(--ink-3);
  font-size: 0.625rem;
  font-weight: 500;
  font-family: var(--font-sans);
  transition: color var(--t-fast) var(--ease);
}

.bottom-nav-item span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bottom-nav-item.router-link-exact-active,
.bottom-nav-item--active {
  color: var(--accent);
  font-weight: 600;
}

/* ── More sheet ─────────────────────────────────────────── */

.sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: flex-end;
  background: rgba(24, 20, 10, 0.38);
  backdrop-filter: var(--blur-overlay);
  -webkit-backdrop-filter: var(--blur-overlay);
}

@media (min-width: 641px) {
  .sheet-overlay {
    display: none;
  }
}

.sheet {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-bottom: 0;
  border-radius: var(--r-card) var(--r-card) 0 0;
  box-shadow: var(--shadow-lg);
  padding: 10px 14px calc(18px + env(safe-area-inset-bottom, 0));
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sheet-grip {
  width: 38px;
  height: 4px;
  border-radius: var(--r-pill);
  background: var(--hairline-strong);
  align-self: center;
  margin-bottom: 10px;
}

.sheet-title {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3);
  padding: 0 10px 6px;
}

.sheet-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 10px;
  border-radius: var(--r-inner);
  color: var(--ink);
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  transition: background var(--t-fast) var(--ease), color var(--t-fast) var(--ease);
}

.sheet-item:active {
  background: var(--surface-hover);
}

.sheet-item.router-link-exact-active {
  background: var(--accent-soft);
  color: var(--accent-ink);
}

.sheet-enter-active,
.sheet-leave-active {
  transition: opacity var(--t-med) var(--ease);
}

.sheet-enter-active .sheet,
.sheet-leave-active .sheet {
  transition: transform var(--t-med) var(--ease-out);
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}

.sheet-enter-from .sheet,
.sheet-leave-to .sheet {
  transform: translateY(100%);
}

@media (prefers-reduced-motion: reduce) {
  .sheet-enter-active .sheet,
  .sheet-leave-active .sheet {
    transition: none;
  }
}
</style>
