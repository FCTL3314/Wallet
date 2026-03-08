<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick, type Component, type CSSProperties } from 'vue'
import { useRouter } from 'vue-router'
import {
  PhWallet,
  PhCurrencyDollar,
  PhBank,
  PhCreditCard,
  PhBriefcase,
  PhArrowCircleUp,
  PhChartBar,
  PhListBullets,
  PhChartLine,
  PhCheckCircle,
  PhX,
} from '@phosphor-icons/vue'
import { useOnboardingStore } from '../stores/onboarding'

interface OnboardingStep {
  icon: Component
  title: string
  description: string
  tip: string
  route: string | null
  target: string | null
  badge?: string
  isModal?: boolean
}

const steps: OnboardingStep[] = [
  {
    icon: PhWallet,
    title: 'Welcome to Wallet!',
    description: 'Wallet helps you track your income, monitor account balances, and plan your budget — all in one place. This quick guide will walk you through the main features.',
    tip: 'The setup only takes a few minutes. Follow the steps in order for the best experience.',
    route: null,
    target: null,
    isModal: true,
  },
  {
    icon: PhCurrencyDollar,
    title: 'Add Your Currencies',
    description: 'Start by adding the currencies you use (USD, EUR, etc.). Every account and transaction is tied to a currency.',
    tip: 'Enter a code (e.g. "USD") and a symbol (e.g. "$"), then click the + button.',
    route: '/references',
    target: 'currencies-section',
    badge: 'Step 1',
  },
  {
    icon: PhBank,
    title: 'Create Storage Locations',
    description: 'Storage locations are places where you hold money — a bank, a physical wallet, a crypto exchange, etc.',
    tip: 'Enter a name and click + to add a location.',
    route: '/references',
    target: 'storage-locations-section',
    badge: 'Step 2',
  },
  {
    icon: PhCreditCard,
    title: 'Set Up Storage Accounts',
    description: "A storage account combines a location with a currency. This is the actual account you'll track — e.g. Chase Bank in USD.",
    tip: 'Pick a location and a currency, then click +.',
    route: '/references',
    target: 'storage-accounts-section',
    badge: 'Step 3',
  },
  {
    icon: PhBriefcase,
    title: 'Add Income Sources',
    description: "Income sources categorize where your money comes from — salary, freelance, investments, etc. You'll pick one when recording income.",
    tip: 'Enter a name and click + to create an income source.',
    route: '/references',
    target: 'income-sources-section',
    badge: 'Step 4',
  },
  {
    icon: PhArrowCircleUp,
    title: 'Record Your Income',
    description: 'Use the Income page to log every payment you receive. Each entry links to an account, an income source, and a date.',
    tip: 'Click "+ Add Income" to open the form. Fill in the amount, account, and source.',
    route: '/transactions',
    target: 'add-income-btn',
    badge: 'Step 5',
  },
  {
    icon: PhChartBar,
    title: 'Take Balance Snapshots',
    description: "A balance snapshot records how much is in each account at a point in time. These power your net worth chart on the Dashboard.",
    tip: 'Click "+ Add Snapshot", pick the account, and enter the current balance.',
    route: '/balance-snapshots',
    target: 'add-snapshot-btn',
    badge: 'Step 6',
  },
  {
    icon: PhListBullets,
    title: 'Plan Regular Expenses',
    description: 'Add recurring monthly expenses (rent, subscriptions, groceries) with a planned budget amount.',
    tip: 'Click "+ Add Category", enter the name and monthly budget.',
    route: '/expenses',
    target: 'add-expense-btn',
    badge: 'Step 7',
  },
  {
    icon: PhChartLine,
    title: 'Explore the Dashboard',
    description: 'The Dashboard shows your financial overview: balance by currency, income trends, income breakdown by source, and a summary table.',
    tip: 'Use the period filter to zoom in on different time ranges.',
    route: '/',
    target: 'dashboard-period-filter',
    badge: 'Step 8',
  },
  {
    icon: PhCheckCircle,
    title: "You're All Set!",
    description: "You now know everything you need to get started. Dive in and start tracking your finances!",
    tip: 'You can replay this guide anytime from Settings.',
    route: null,
    target: null,
    isModal: true,
  },
]

const PADDING = 10
const TOOLTIP_WIDTH = 340
const TOOLTIP_HEIGHT_EST = 320

const onboarding = useOnboardingStore()
const router = useRouter()

const currentIndex = ref(0)
const isNavigating = ref(false)
const highlightRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)
let highlightedEl: Element | null = null

const currentStep = computed(() => steps[currentIndex.value] as OnboardingStep)
const isFirst = computed(() => currentIndex.value === 0)
const isLast = computed(() => currentIndex.value === steps.length - 1)
const isModalStep = computed(() => !!currentStep.value.isModal)

const badgeLabel = computed(() => {
  if (currentIndex.value === 0) return 'Overview'
  if (isLast.value) return 'Done'
  return currentStep.value.badge ?? ''
})

// ── Tooltip positioning ──────────────────────────────────────

const tooltipStyle = computed((): CSSProperties => {
  const rect = highlightRect.value
  const vw = window.innerWidth
  const vh = window.innerHeight
  const clampedWidth = Math.min(TOOLTIP_WIDTH, vw - 32)

  // Fallback: center-bottom of screen when element not found yet
  if (!rect) {
    return {
      position: 'fixed',
      bottom: '32px',
      left: `${Math.max(16, (vw - clampedWidth) / 2)}px`,
      width: `${clampedWidth}px`,
    }
  }

  const gap = 16
  const spaceBelow = vh - (rect.y + rect.height + PADDING)
  const spaceAbove = rect.y - PADDING

  if (spaceBelow >= TOOLTIP_HEIGHT_EST || spaceBelow >= spaceAbove) {
    const top = rect.y + rect.height + PADDING + gap
    const left = Math.max(16, Math.min(vw - clampedWidth - 16, rect.x + rect.width / 2 - clampedWidth / 2))
    return { position: 'fixed', top: `${top}px`, left: `${left}px`, width: `${clampedWidth}px` }
  } else {
    const bottom = vh - (rect.y - PADDING - gap)
    const left = Math.max(16, Math.min(vw - clampedWidth - 16, rect.x + rect.width / 2 - clampedWidth / 2))
    return { position: 'fixed', bottom: `${bottom}px`, left: `${left}px`, width: `${clampedWidth}px` }
  }
})

// ── Highlight helpers ────────────────────────────────────────

function clearHighlight() {
  if (highlightedEl) {
    highlightedEl.classList.remove('ob-highlighted')
    highlightedEl = null
  }
  highlightRect.value = null
}

function updateRect(el: Element) {
  if (highlightedEl && highlightedEl !== el) {
    highlightedEl.classList.remove('ob-highlighted')
  }
  highlightedEl = el
  el.classList.add('ob-highlighted')
  const r = el.getBoundingClientRect()
  highlightRect.value = { x: r.left, y: r.top, width: r.width, height: r.height }
}

function recalcRect() {
  const step = steps[currentIndex.value]
  if (!step?.target || step.isModal) return
  const el = document.querySelector(`[data-onboarding="${step.target}"]`)
  if (el) {
    const r = el.getBoundingClientRect()
    highlightRect.value = { x: r.left, y: r.top, width: r.width, height: r.height }
  }
}

// ── Navigation helpers ───────────────────────────────────────

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

async function activateStep(index: number) {
  const step = steps[index]
  if (!step) return

  if (step.isModal) {
    clearHighlight()
    return
  }

  isNavigating.value = true

  if (step.route && router.currentRoute.value.path !== step.route) {
    await router.push(step.route)
    await nextTick()
    await sleep(350)
  } else {
    await nextTick()
    await sleep(50)
  }

  if (step.target) {
    // Retry up to 10 times (every 150ms = up to 1.5s) to handle slow-mounting pages
    let el: Element | null = null
    for (let i = 0; i < 10; i++) {
      el = document.querySelector(`[data-onboarding="${step.target}"]`)
      if (el) break
      await sleep(150)
    }
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      await sleep(400)
      updateRect(el)
    } else {
      highlightRect.value = null
    }
  }

  isNavigating.value = false
}

// ── Actions ──────────────────────────────────────────────────

async function goToStep(index: number) {
  if (index === currentIndex.value) return
  currentIndex.value = index
}

async function next() {
  if (isLast.value) {
    done()
    return
  }
  currentIndex.value++
}

function prev() {
  if (isFirst.value) return
  currentIndex.value--
}

function done() {
  onboarding.finish()
  router.push('/')
}

function skip() {
  onboarding.finish()
}

function close() {
  onboarding.finish()
}

function handleKeydown(e: KeyboardEvent) {
  if (!onboarding.active) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
}

function handleOverlayClick() {
  close()
}

// ── Watchers ─────────────────────────────────────────────────

watch(
  () => onboarding.active,
  async (val) => {
    if (val) {
      currentIndex.value = 0
      await activateStep(0)
    } else {
      clearHighlight()
    }
  },
)

watch(currentIndex, (idx) => activateStep(idx))

// ── Lifecycle ────────────────────────────────────────────────

onMounted(() => {
  window.addEventListener('scroll', recalcRect, true)
  window.addEventListener('resize', recalcRect)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('scroll', recalcRect, true)
  window.removeEventListener('resize', recalcRect)
  document.removeEventListener('keydown', handleKeydown)
  clearHighlight()
})
</script>

<template>
  <Teleport to="body">
    <!-- ── MODAL MODE ─────────────────────────────────────────── -->
    <Transition name="ob-overlay">
      <div
        v-if="onboarding.active && isModalStep"
        class="ob-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="currentStep.title"
        @click.self="close"
      >
        <div class="ob-card">
          <!-- Close -->
          <button class="ob-close" aria-label="Close guide" @click="close">
            <PhX :size="18" weight="bold" />
          </button>

          <!-- Badge -->
          <div class="ob-badge">{{ badgeLabel }}</div>

          <!-- Icon -->
          <div
            class="ob-icon-wrap"
            :class="{ 'ob-icon-wrap--success': isLast }"
          >
            <component :is="currentStep.icon" :size="40" weight="duotone" />
          </div>

          <!-- Text -->
          <h2 class="ob-title">{{ currentStep.title }}</h2>
          <p class="ob-description">{{ currentStep.description }}</p>

          <!-- Tip box -->
          <div class="ob-tip">
            <span class="ob-tip-label">Quick tip</span>
            <p class="ob-tip-text">{{ currentStep.tip }}</p>
          </div>

          <!-- Dots -->
          <div class="ob-dots" role="tablist" aria-label="Guide progress">
            <button
              v-for="(_, i) in steps"
              :key="i"
              class="ob-dot"
              :class="{ 'ob-dot--active': i === currentIndex }"
              role="tab"
              :aria-selected="i === currentIndex"
              :aria-label="`Go to step ${i + 1}`"
              @click="goToStep(i)"
            />
          </div>

          <!-- Actions -->
          <div class="ob-actions">
            <button class="btn btn-secondary btn-sm ob-skip" @click="skip">Skip</button>
            <div class="ob-nav-btns">
              <button v-if="!isFirst" class="btn btn-secondary btn-sm" @click="prev">Previous</button>
              <button class="btn btn-primary btn-sm" @click="next">
                {{ isLast ? 'Done' : 'Get Started' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── SPOTLIGHT MODE ─────────────────────────────────────── -->
    <template v-if="onboarding.active && !isModalStep">
      <!-- SVG darkening overlay with cutout -->
      <svg
        v-if="highlightRect"
        class="ob-spotlight-svg"
        aria-hidden="true"
        @click="handleOverlayClick"
      >
        <defs>
          <mask id="ob-spotlight-mask">
            <rect width="100%" height="100%" fill="white" />
            <rect
              :x="highlightRect.x - PADDING"
              :y="highlightRect.y - PADDING"
              :width="highlightRect.width + PADDING * 2"
              :height="highlightRect.height + PADDING * 2"
              rx="10"
              fill="black"
            />
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(0,0,0,0.55)" mask="url(#ob-spotlight-mask)" />
      </svg>

      <!-- Fallback full overlay while navigating/no rect yet -->
      <div
        v-if="!highlightRect"
        class="ob-spotlight-loading"
        aria-hidden="true"
      />

      <!-- Floating tooltip (always visible in spotlight mode) -->
      <Transition name="ob-tooltip-fade">
        <div
          v-if="!isNavigating || highlightRect"
          class="ob-tooltip"
          :style="tooltipStyle"
          role="dialog"
          aria-modal="true"
          :aria-label="currentStep.title"
        >
          <!-- Close -->
          <button class="ob-close ob-close--inline" aria-label="Close guide" @click="close">
            <PhX :size="16" weight="bold" />
          </button>

          <!-- Badge -->
          <div class="ob-badge ob-badge--sm">{{ badgeLabel }}</div>

          <!-- Icon + Title -->
          <div class="ob-tooltip-header">
            <div class="ob-tooltip-icon">
              <component :is="currentStep.icon" :size="28" weight="duotone" />
            </div>
            <h3 class="ob-tooltip-title">{{ currentStep.title }}</h3>
          </div>

          <!-- Description -->
          <p class="ob-tooltip-desc">{{ currentStep.description }}</p>

          <!-- Tip -->
          <div class="ob-tip ob-tip--compact">
            <span class="ob-tip-label">Tip</span>
            <p class="ob-tip-text">{{ currentStep.tip }}</p>
          </div>

          <!-- Dots -->
          <div class="ob-dots" role="tablist" aria-label="Guide progress">
            <button
              v-for="(_, i) in steps"
              :key="i"
              class="ob-dot"
              :class="{ 'ob-dot--active': i === currentIndex }"
              role="tab"
              :aria-selected="i === currentIndex"
              :aria-label="`Go to step ${i + 1}`"
              @click="goToStep(i)"
            />
          </div>

          <!-- Actions -->
          <div class="ob-actions">
            <button class="btn btn-secondary btn-sm ob-skip" @click="skip">Skip</button>
            <div class="ob-nav-btns">
              <button v-if="!isFirst" class="btn btn-secondary btn-sm" @click="prev">Previous</button>
              <button class="btn btn-primary btn-sm" @click="next">Next</button>
            </div>
          </div>
        </div>
      </Transition>
    </template>
  </Teleport>
</template>

<style scoped>
/* ── Shared overlay backdrop (modal mode) ───────────────── */

.ob-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.52);
  backdrop-filter: var(--blur-overlay);
  -webkit-backdrop-filter: var(--blur-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 16px;
}

/* ── Modal card ─────────────────────────────────────────── */

.ob-card {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-modal);
  padding: 40px 36px 32px;
  width: 100%;
  max-width: 560px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* ── Close button (shared) ──────────────────────────────── */

.ob-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--card-border);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s, color 0.18s;
  flex-shrink: 0;
}

.ob-close:hover {
  background: rgba(0, 0, 0, 0.07);
  color: var(--text-primary);
}

[data-theme="dark"] .ob-close:hover {
  background: rgba(255, 255, 255, 0.09);
}

/* Inline variant for the tooltip (not absolute-positioned) */
.ob-close--inline {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
}

/* ── Progress badge ─────────────────────────────────────── */

.ob-badge {
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-accent);
  background: rgba(var(--color-accent-rgb), 0.10);
  border: 1px solid rgba(var(--color-accent-rgb), 0.18);
  border-radius: var(--radius-chip);
  padding: 4px 12px;
  margin-bottom: 24px;
  align-self: center;
}

.ob-badge--sm {
  font-size: 0.7rem;
  padding: 3px 10px;
  margin-bottom: 10px;
}

/* ── Icon wrap (modal mode) ─────────────────────────────── */

.ob-icon-wrap {
  width: 80px;
  height: 80px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  background: rgba(var(--color-accent-rgb), 0.10);
  color: var(--color-accent);
  transition: background 0.25s, color 0.25s;
}

.ob-icon-wrap--success {
  background: rgba(31, 160, 104, 0.12);
  color: var(--color-income);
}

/* ── Modal text ─────────────────────────────────────────── */

.ob-title {
  font-family: var(--font-heading);
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  line-height: 1.3;
}

.ob-description {
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--text-secondary);
  margin-bottom: 20px;
  max-width: 440px;
}

/* ── Tip box ────────────────────────────────────────────── */

.ob-tip {
  width: 100%;
  background: rgba(var(--color-accent-rgb), 0.07);
  border: 1px solid rgba(var(--color-accent-rgb), 0.14);
  border-radius: 16px;
  padding: 14px 16px;
  text-align: left;
  margin-bottom: 24px;
}

.ob-tip--compact {
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.ob-tip-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--color-accent);
  margin-bottom: 6px;
}

.ob-tip-text {
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--text-secondary);
  margin: 0;
}

/* ── Dots ───────────────────────────────────────────────── */

.ob-dots {
  display: flex;
  gap: 7px;
  margin-bottom: 24px;
}

.ob-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  background: rgba(var(--color-accent-rgb), 0.20);
  cursor: pointer;
  padding: 0;
  transition: background 0.2s, transform 0.2s var(--ease-spring), width 0.2s var(--ease-spring);
}

.ob-dot--active {
  background: var(--color-accent);
  width: 22px;
  border-radius: 4px;
}

.ob-dot:hover:not(.ob-dot--active) {
  background: rgba(var(--color-accent-rgb), 0.40);
  transform: scale(1.2);
}

/* ── Actions row ────────────────────────────────────────── */

.ob-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}

.ob-skip {
  color: var(--text-secondary);
}

.ob-nav-btns {
  display: flex;
  gap: 8px;
}

/* ── Spotlight SVG overlay ──────────────────────────────── */

.ob-spotlight-svg {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 400;
  pointer-events: all;
  cursor: default;
}

/* Dimmer shown while navigating (no rect yet) */
.ob-spotlight-loading {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 400;
  pointer-events: all;
}

/* ── Floating tooltip ───────────────────────────────────── */

.ob-tooltip {
  /* position is set via :style binding */
  z-index: 401;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 0;
}

.ob-tooltip-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.ob-tooltip-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(var(--color-accent-rgb), 0.10);
  color: var(--color-accent);
}

.ob-tooltip-title {
  font-family: var(--font-heading);
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
  margin: 0;
}

.ob-tooltip-desc {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0 0 12px;
}

/* ── Transitions ────────────────────────────────────────── */

.ob-overlay-enter-active { transition: opacity 0.22s ease; }
.ob-overlay-leave-active { transition: opacity 0.18s ease; }
.ob-overlay-enter-from,
.ob-overlay-leave-to { opacity: 0; }

.ob-tooltip-fade-enter-active { transition: opacity 0.2s ease, transform 0.22s var(--ease-smooth); }
.ob-tooltip-fade-leave-active { transition: opacity 0.15s ease; }
.ob-tooltip-fade-enter-from   { opacity: 0; transform: translateY(8px); }
.ob-tooltip-fade-leave-to     { opacity: 0; }

/* ── Mobile responsive ──────────────────────────────────── */

@media (max-width: 640px) {
  .ob-overlay {
    align-items: flex-end;
    padding: 0;
  }

  .ob-card {
    max-width: none;
    border-radius: 24px 24px 0 0;
    padding: 28px 20px 24px;
  }

  .ob-card::before {
    content: '';
    display: block;
    position: absolute;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    width: 36px;
    height: 4px;
    background: rgba(0, 0, 0, 0.12);
    border-radius: 9999px;
  }

  [data-theme="dark"] .ob-card::before {
    background: rgba(255, 255, 255, 0.14);
  }

  .ob-title {
    font-size: 1.2rem;
  }

  .ob-description {
    font-size: 0.875rem;
  }

  .ob-tooltip {
    border-radius: 16px 16px 0 0 !important;
    bottom: 0 !important;
    top: auto !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    max-height: 60vh;
    overflow-y: auto;
  }
}
</style>
