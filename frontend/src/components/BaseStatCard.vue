<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, useTemplateRef, watch } from 'vue'
import { PhInfo } from '@phosphor-icons/vue'

const VIEWPORT_MARGIN = 12
const ANCHOR_GAP = 10
const ARROW_INSET = 16

const props = defineProps<{
  label: string
  variant?: 'income' | 'expense' | 'profit'
  hint?: string
  flat?: boolean
}>()

const tooltipId = useId()
const hintRef = useTemplateRef<HTMLElement>('hintRef')
const popupRef = useTemplateRef<HTMLElement>('popupRef')

const tooltipVisible = ref(false)
const tooltipPlaced = ref(false)
const tooltipBelow = ref(false)
const tooltipStyle = ref<Record<string, string>>({})

let focusFromPointer = false

function placeTooltip() {
  const anchor = hintRef.value
  const popup = popupRef.value
  if (!anchor || !popup) return

  const rect = anchor.getBoundingClientRect()
  const viewportWidth = document.documentElement.clientWidth
  const width = popup.offsetWidth
  const height = popup.offsetHeight
  const half = width / 2

  const anchorCenter = rect.left + rect.width / 2
  const minCenter = VIEWPORT_MARGIN + half
  const maxCenter = viewportWidth - VIEWPORT_MARGIN - half
  const center =
    maxCenter < minCenter ? viewportWidth / 2 : Math.min(Math.max(anchorCenter, minCenter), maxCenter)

  const below = rect.top - height - ANCHOR_GAP < VIEWPORT_MARGIN
  const arrowX = Math.min(Math.max(anchorCenter - (center - half), ARROW_INSET), width - ARROW_INSET)

  tooltipBelow.value = below
  tooltipStyle.value = {
    left: `${center + window.scrollX}px`,
    top: below
      ? `${rect.bottom + window.scrollY + ANCHOR_GAP}px`
      : `${rect.top + window.scrollY - ANCHOR_GAP}px`,
    '--arrow-x': `${arrowX}px`,
  }
  tooltipPlaced.value = true
}

async function showTooltip() {
  if (!props.hint || tooltipVisible.value) return
  tooltipPlaced.value = false
  tooltipVisible.value = true
  await nextTick()
  placeTooltip()
}

function hideTooltip() {
  tooltipVisible.value = false
  tooltipPlaced.value = false
}

function toggleTooltip() {
  if (tooltipVisible.value) hideTooltip()
  else showTooltip()
}

function onPointerEnter(event: PointerEvent) {
  if (event.pointerType !== 'mouse') return
  showTooltip()
}

function onPointerLeave(event: PointerEvent) {
  if (event.pointerType !== 'mouse') return
  hideTooltip()
}

function onPointerDown() {
  focusFromPointer = true
}

function onFocus() {
  if (focusFromPointer) return
  showTooltip()
}

function onBlur() {
  focusFromPointer = false
  hideTooltip()
}

watch(tooltipVisible, (visible) => {
  if (visible) window.addEventListener('resize', placeTooltip)
  else window.removeEventListener('resize', placeTooltip)
})

onBeforeUnmount(() => window.removeEventListener('resize', placeTooltip))
</script>

<template>
  <div :class="[!props.flat && 'card', 'stat-card', variant ? `stat-card--${variant}` : '']">
    <div class="stat-label">
      {{ label }}
      <button
        v-if="hint"
        ref="hintRef"
        type="button"
        class="stat-hint"
        :aria-label="`About ${label}`"
        :aria-expanded="tooltipVisible"
        :aria-describedby="tooltipVisible ? tooltipId : undefined"
        @pointerenter="onPointerEnter"
        @pointerleave="onPointerLeave"
        @pointerdown="onPointerDown"
        @focus="onFocus"
        @blur="onBlur"
        @click="toggleTooltip"
        @keydown.esc="hideTooltip"
      >
        <PhInfo :size="13" weight="bold" />
      </button>
    </div>
    <slot />
  </div>
  <Teleport to="body">
    <div
      v-if="tooltipVisible && hint"
      :id="tooltipId"
      ref="popupRef"
      class="stat-hint-popup"
      :class="{ 'stat-hint-popup--below': tooltipBelow, 'stat-hint-popup--placed': tooltipPlaced }"
      :style="tooltipStyle"
      role="tooltip"
    >
      <p class="stat-hint-text">{{ hint }}</p>
    </div>
  </Teleport>
</template>

<style scoped>
.stat-label {
  display: flex;
  align-items: center;
  gap: 5px;
}

.stat-hint {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: 0;
  background: none;
  color: var(--text-placeholder);
  cursor: pointer;
  transition: color 0.15s;
}

.stat-hint:focus-visible {
  color: var(--text-secondary);
}

@media (hover: hover) {
  .stat-hint:hover {
    color: var(--text-secondary);
  }
}
</style>

<style>
.stat-hint-popup {
  position: absolute;
  width: min(260px, calc(100vw - 24px));
  transform: translate(-50%, -100%);
  background: rgba(15, 18, 28, 0.92);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  padding: 12px 14px;
  pointer-events: none;
  opacity: 0;
  z-index: 9999;
}

.stat-hint-popup--placed {
  opacity: 1;
}

.stat-hint-popup--below {
  transform: translate(-50%, 0);
}

.stat-hint-popup::after {
  content: '';
  position: absolute;
  top: 100%;
  left: var(--arrow-x, 50%);
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: rgba(15, 18, 28, 0.92);
}

.stat-hint-popup--below::after {
  top: auto;
  bottom: 100%;
  border-top-color: transparent;
  border-bottom-color: rgba(15, 18, 28, 0.92);
}

.stat-hint-text {
  font-size: 0.72rem;
  font-weight: 400;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.88);
  white-space: pre-line;
  margin: 0;
}
</style>
