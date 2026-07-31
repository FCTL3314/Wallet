<script lang="ts">
const modalStack: symbol[] = []

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
import { nextTick, onBeforeUnmount, ref, useId, useTemplateRef, watch } from 'vue'
import BaseButton from './BaseButton.vue'

const props = withDefaults(defineProps<{
  title: string
  show: boolean
  dirty?: boolean
  submitting?: boolean
  submitLabel?: string
  cancelLabel?: string
  discardMessage?: string
}>(), {
  dirty: false,
  submitting: false,
  submitLabel: 'Save',
  cancelLabel: 'Cancel',
  discardMessage: 'You have unsaved changes. Discard them?',
})

const emit = defineEmits<{ close: []; submit: [] }>()

const instanceKey = Symbol('base-modal')
const titleId = useId()
const dialog = useTemplateRef<HTMLElement>('dialog')
const confirmingDiscard = ref(false)

let opener: HTMLElement | null = null
let overlayPressed = false

function focusableItems(): HTMLElement[] {
  const root = dialog.value
  if (!root) return []
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
    .filter((el) => el.getClientRects().length > 0)
}

function focusFirst() {
  const items = focusableItems()
  const target = items.find((el) => !el.hasAttribute('readonly')) ?? items[0]
  if (target) target.focus()
  else dialog.value?.focus()
}

function focusInside(selector: string) {
  dialog.value?.querySelector<HTMLElement>(selector)?.focus()
}

function trapFocus(event: KeyboardEvent) {
  const root = dialog.value
  if (!root) return
  const items = focusableItems()
  if (!items.length) {
    event.preventDefault()
    return
  }
  const first = items[0]
  const last = items[items.length - 1]
  if (!first || !last) return
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

function isTopmost(): boolean {
  return modalStack[modalStack.length - 1] === instanceKey
}

function onKeydown(event: KeyboardEvent) {
  if (!props.show || !isTopmost()) return
  if (event.key === 'Escape') {
    const active = document.activeElement
    if (active instanceof HTMLElement && active.closest('[data-confirm-pending]')) return
    event.preventDefault()
    event.stopPropagation()
    requestClose()
    return
  }
  if (event.key === 'Tab') trapFocus(event)
}

function requestClose() {
  if (props.submitting) return
  if (props.dirty && !confirmingDiscard.value) {
    confirmingDiscard.value = true
    nextTick(() => focusInside('[data-modal-keep]'))
    return
  }
  confirmingDiscard.value = false
  emit('close')
}

function onOverlayMousedown(event: MouseEvent) {
  overlayPressed = event.target === event.currentTarget
}

function onOverlayClick(event: MouseEvent) {
  if (!overlayPressed || event.target !== event.currentTarget) return
  overlayPressed = false
  requestClose()
}

function onSubmit() {
  if (props.submitting) return
  emit('submit')
}

function detach() {
  const index = modalStack.lastIndexOf(instanceKey)
  if (index !== -1) modalStack.splice(index, 1)
  document.removeEventListener('keydown', onKeydown, true)
  confirmingDiscard.value = false
  overlayPressed = false
}

function restoreFocus() {
  const target = opener
  opener = null
  if (target?.isConnected) target.focus()
}

watch(() => props.show, async (visible) => {
  if (visible) {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    modalStack.push(instanceKey)
    document.addEventListener('keydown', onKeydown, true)
    await nextTick()
    focusFirst()
  } else {
    detach()
    restoreFocus()
  }
}, { immediate: true })

onBeforeUnmount(detach)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show"
        class="modal-overlay"
        @mousedown="onOverlayMousedown"
        @click="onOverlayClick"
      >
        <div
          ref="dialog"
          class="modal"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
        >
          <h2 :id="titleId">{{ title }}</h2>
          <form @submit.prevent="onSubmit">
            <slot />
            <div v-if="confirmingDiscard" class="modal-discard" role="alert">
              <p class="modal-discard-text">{{ discardMessage }}</p>
              <div class="modal-discard-actions">
                <BaseButton
                  data-modal-keep
                  variant="secondary"
                  size="sm"
                  @click="confirmingDiscard = false"
                >
                  Keep editing
                </BaseButton>
                <BaseButton variant="danger" size="sm" @click="emit('close')">
                  Discard changes
                </BaseButton>
              </div>
            </div>
            <div class="modal-actions">
              <BaseButton variant="secondary" :disabled="submitting" @click="requestClose">
                {{ cancelLabel }}
              </BaseButton>
              <BaseButton variant="primary" type="submit" :loading="submitting">
                {{ submitLabel }}
              </BaseButton>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
