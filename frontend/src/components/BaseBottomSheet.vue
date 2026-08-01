<script lang="ts">
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')
</script>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, useId, useTemplateRef, watch } from 'vue'
import { PhX } from '@phosphor-icons/vue'

withDefaults(defineProps<{
  title: string
  closeLabel?: string
}>(), {
  closeLabel: 'Done',
})

const open = defineModel<boolean>({ required: true })

const titleId = useId()
const panel = useTemplateRef<HTMLElement>('panel')

let opener: HTMLElement | null = null
let overlayPressed = false
let previousBodyOverflow: string | null = null

function focusableItems(): HTMLElement[] {
  const root = panel.value
  if (!root) return []
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
    .filter((el) => el.getClientRects().length > 0)
}

function trapFocus(event: KeyboardEvent) {
  const root = panel.value
  if (!root) return
  const items = focusableItems()
  const first = items[0]
  const last = items[items.length - 1]
  if (!first || !last) {
    event.preventDefault()
    return
  }
  const active = document.activeElement
  const inside = active instanceof HTMLElement && root.contains(active)
  if (event.shiftKey) {
    if (!inside || active === first) {
      event.preventDefault()
      last.focus()
    }
  } else if (!inside || active === last) {
    event.preventDefault()
    first.focus()
  }
}

function onKeydown(event: KeyboardEvent) {
  if (!open.value) return
  if (event.key === 'Escape') {
    const active = document.activeElement
    if (active instanceof HTMLElement && active.closest('[data-confirm-pending]')) return
    event.preventDefault()
    event.stopPropagation()
    close()
    return
  }
  if (event.key === 'Tab') trapFocus(event)
}

function close() {
  open.value = false
}

function onOverlayMousedown(event: MouseEvent) {
  overlayPressed = event.target === event.currentTarget
}

function onOverlayClick(event: MouseEvent) {
  if (!overlayPressed || event.target !== event.currentTarget) return
  overlayPressed = false
  close()
}

function lockScroll() {
  if (previousBodyOverflow !== null) return
  previousBodyOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
}

function unlockScroll() {
  if (previousBodyOverflow === null) return
  document.body.style.overflow = previousBodyOverflow
  previousBodyOverflow = null
}

function detach() {
  document.removeEventListener('keydown', onKeydown, true)
  overlayPressed = false
  unlockScroll()
}

function restoreFocus() {
  const target = opener
  opener = null
  if (target?.isConnected) target.focus()
}

watch(open, async (visible) => {
  if (visible) {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    document.addEventListener('keydown', onKeydown, true)
    lockScroll()
    await nextTick()
    const items = focusableItems()
    const target = items.find((el) => !el.hasAttribute('data-sheet-close')) ?? items[0]
    if (target) target.focus()
    else panel.value?.focus()
  } else {
    detach()
    restoreFocus()
  }
}, { immediate: true })

onBeforeUnmount(detach)
</script>

<template>
  <Teleport to="body">
    <Transition name="bottom-sheet">
      <div
        v-if="open"
        class="bottom-sheet-overlay"
        @mousedown="onOverlayMousedown"
        @click="onOverlayClick"
      >
        <div
          ref="panel"
          class="bottom-sheet"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
        >
          <span class="bottom-sheet-grip" aria-hidden="true" />
          <header class="bottom-sheet-head">
            <h2 :id="titleId" class="bottom-sheet-title">{{ title }}</h2>
            <button
              type="button"
              class="bottom-sheet-dismiss"
              aria-label="Close"
              data-sheet-close
              @click="close"
            >
              <PhX :size="16" weight="bold" />
            </button>
          </header>
          <div class="bottom-sheet-body">
            <slot />
          </div>
          <div class="bottom-sheet-foot">
            <button type="button" class="btn btn--primary bottom-sheet-done" @click="close">
              {{ closeLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.bottom-sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: flex-end;
  background: rgba(28, 29, 26, 0.45);
  backdrop-filter: var(--blur-overlay);
  -webkit-backdrop-filter: var(--blur-overlay);
}

.bottom-sheet {
  width: 100%;
  max-width: 100%;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-bottom: 0;
  border-radius: var(--r-card) var(--r-card) 0 0;
  box-shadow: var(--shadow-lg);
  padding: 10px 16px calc(16px + env(safe-area-inset-bottom, 0px));
  outline: none;
}

.bottom-sheet-grip {
  width: 38px;
  height: 4px;
  border-radius: var(--r-pill);
  background: var(--hairline-strong);
  align-self: center;
  flex: 0 0 auto;
}

.bottom-sheet-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0 12px;
  flex: 0 0 auto;
}

.bottom-sheet-title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bottom-sheet-dismiss {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--r-pill);
  border: 1px solid var(--hairline);
  background: var(--surface-2);
  color: var(--ink-2);
  cursor: pointer;
  touch-action: manipulation;
  transition: background var(--t-fast) var(--ease), color var(--t-fast) var(--ease);
}

.bottom-sheet-dismiss:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.bottom-sheet-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.bottom-sheet-foot {
  flex: 0 0 auto;
  padding-top: 14px;
}

.bottom-sheet-done {
  width: 100%;
  justify-content: center;
}

@media (hover: hover) {
  .bottom-sheet-dismiss:hover {
    background: var(--surface-hover);
    color: var(--ink);
  }
}

.bottom-sheet-enter-active,
.bottom-sheet-leave-active {
  transition: opacity var(--t-med) var(--ease);
}

.bottom-sheet-enter-active .bottom-sheet,
.bottom-sheet-leave-active .bottom-sheet {
  transition: transform var(--t-med) var(--ease-out);
}

.bottom-sheet-enter-from,
.bottom-sheet-leave-to {
  opacity: 0;
}

.bottom-sheet-enter-from .bottom-sheet,
.bottom-sheet-leave-to .bottom-sheet {
  transform: translateY(100%);
}

@media (prefers-reduced-motion: reduce) {
  .bottom-sheet-enter-active .bottom-sheet,
  .bottom-sheet-leave-active .bottom-sheet {
    transition: none;
  }
}
</style>
