<script setup lang="ts">
import {
  ref,
  computed,
  watch,
  onMounted,
  onUnmounted,
  nextTick,
  useTemplateRef,
  type Component,
  type CSSProperties,
} from 'vue'
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

interface StepLocation {
  path: string
  query?: Record<string, string>
}

interface OnboardingStep {
  icon: Component
  title: string
  description: string
  tip: string
  location: StepLocation | null
  target: string | null
  badge?: string
  isModal?: boolean
}

interface HighlightRect {
  x: number
  y: number
  width: number
  height: number
}

const steps: OnboardingStep[] = [
  {
    icon: PhWallet,
    title: 'Welcome to Wallet!',
    description: 'Wallet helps you track your income, monitor account balances, and plan your budget — all in one place. This quick guide will walk you through the main features.',
    tip: 'The setup only takes a few minutes. Follow the steps in order for the best experience.',
    location: null,
    target: null,
    isModal: true,
  },
  {
    icon: PhCurrencyDollar,
    title: 'Add Your Currencies',
    description: 'Start with the currencies you actually use. Every account, income entry and balance is tied to one, and the currency marked as base is what your totals are converted into.',
    tip: 'Type a name or code in the search field, pick a match from the catalog suggestions, then confirm with the Add button. For something the catalog does not cover, switch to "Add custom currency instead" and enter the code and symbol yourself.',
    location: { path: '/references', query: { tab: 'currencies' } },
    target: 'currencies-section',
    badge: 'Step 1',
  },
  {
    icon: PhBank,
    title: 'Create Storage Locations',
    description: 'Storage locations are the places where you keep money — a bank, a cash wallet, a broker, a crypto exchange. They describe the "where", not the amount.',
    tip: 'Enter the name of the place and confirm with the Add button. Locations can be renamed or removed later from the same list.',
    location: { path: '/references', query: { tab: 'locations' } },
    target: 'storage-locations-section',
    badge: 'Step 2',
  },
  {
    icon: PhCreditCard,
    title: 'Set Up Storage Accounts',
    description: 'A storage account pairs a location with a currency — for example Chase Bank in USD. Income entries and balance snapshots are recorded against these accounts.',
    tip: 'Pick a location and a currency, then confirm with the Add button. Create one account per currency you hold in that place.',
    location: { path: '/references', query: { tab: 'accounts' } },
    target: 'storage-accounts-section',
    badge: 'Step 3',
  },
  {
    icon: PhBriefcase,
    title: 'Add Income Sources',
    description: 'Income sources describe where your money comes from — salary, freelance, dividends. You pick one every time you record income, and the Dashboard breaks your earnings down by them.',
    tip: 'Enter a name and confirm with the Add button. Keep the list short and reusable.',
    location: { path: '/references', query: { tab: 'income' } },
    target: 'income-sources-section',
    badge: 'Step 4',
  },
  {
    icon: PhArrowCircleUp,
    title: 'Record Your Income',
    description: 'Use the Income page to log every payment you receive. Each entry links an amount to a storage account, an income source and a date.',
    tip: 'Use the add button in the page header to open the form, then fill in the amount, the account it landed on, and the source it came from.',
    location: { path: '/transactions' },
    target: 'add-income-btn',
    badge: 'Step 5',
  },
  {
    icon: PhChartBar,
    title: 'Take Balance Snapshots',
    description: 'A balance snapshot records how much sits in each account at a point in time. Snapshots power the net worth chart and the profit figures on the Dashboard.',
    tip: 'Use the add button in the page header, choose an account and enter its current balance. Repeat once a month to build up history.',
    location: { path: '/balance-snapshots' },
    target: 'add-snapshot-btn',
    badge: 'Step 6',
  },
  {
    icon: PhListBullets,
    title: 'Plan Regular Expenses',
    description: 'Plan the costs that come back every month — rent, subscriptions, groceries — by giving each category a budgeted amount.',
    tip: 'Use the add button in the page header, then enter the category name and the amount you budget for it each month.',
    location: { path: '/expenses' },
    target: 'add-expense-btn',
    badge: 'Step 7',
  },
  {
    icon: PhChartLine,
    title: 'Explore the Dashboard',
    description: 'The Dashboard is your financial overview: balance per currency, income trends, a breakdown by source, and a period summary table.',
    tip: 'Switch between the period presets or set a custom range to zoom in on any time span.',
    location: { path: '/' },
    target: 'dashboard-period-filter',
    badge: 'Step 8',
  },
  {
    icon: PhCheckCircle,
    title: "You're All Set!",
    description: 'You now know everything you need to get started. Dive in and start tracking your finances!',
    tip: 'You can replay this guide at any time from the Settings page.',
    location: null,
    target: null,
    isModal: true,
  },
]

const PADDING = 10
const GAP = 16
const VIEWPORT_MARGIN = 16
const TOOLTIP_WIDTH = 340
const TOOLTIP_HEIGHT_EST = 320
const MOBILE_BREAKPOINT = 640
const MOBILE_SAFE_TOP = 96
const MOBILE_TARGET_RATIO = 0.42
const ROUTE_SETTLE_MS = 220
const TARGET_POLL_MS = 60
const TARGET_TIMEOUT_MS = 900
const SCROLL_SETTLE_MS = 520
const TRACK_MS = 1200
const TRACK_SETTLE_MS = 400
const NUDGE_MS = 420

const onboarding = useOnboardingStore()
const router = useRouter()

const cardRef = useTemplateRef<HTMLElement>('card')
const tooltipRef = useTemplateRef<HTMLElement>('tooltip')

const isNavigating = ref(false)
const nudging = ref(false)
const paused = ref(false)
const highlightRect = ref<HighlightRect | null>(null)
const tooltipHeight = ref(TOOLTIP_HEIGHT_EST)
const viewport = ref({ width: window.innerWidth, height: window.innerHeight })

let highlightedEl: Element | null = null
let activationToken = 0
let trackDeadline = 0
let rafId: number | null = null
let nudgeTimer: ReturnType<typeof setTimeout> | null = null

const targetObserver = new ResizeObserver(() => syncRect())
const tooltipObserver = new ResizeObserver((entries) => {
  const entry = entries[0]
  if (entry) tooltipHeight.value = (entry.target as HTMLElement).offsetHeight
})

const currentIndex = computed<number>({
  get: () => clamp(onboarding.stepIndex, 0, steps.length - 1),
  set: (value) => onboarding.goToStep(clamp(value, 0, steps.length - 1)),
})

const currentStep = computed(() => steps[currentIndex.value] as OnboardingStep)
const isFirst = computed(() => currentIndex.value === 0)
const isLast = computed(() => currentIndex.value === steps.length - 1)
const isModalStep = computed(() => !!currentStep.value.isModal)
const isMobile = computed(() => viewport.value.width <= MOBILE_BREAKPOINT)

const badgeLabel = computed(() => {
  if (isFirst.value) return 'Overview'
  if (isLast.value) return 'Done'
  return currentStep.value.badge ?? ''
})

const tooltipWidth = computed(() =>
  Math.min(TOOLTIP_WIDTH, Math.max(240, viewport.value.width - VIEWPORT_MARGIN * 2)),
)

const tooltipStyle = computed((): CSSProperties => {
  const rect = highlightRect.value
  const { width: vw, height: vh } = viewport.value
  const width = tooltipWidth.value
  const base: CSSProperties = {
    width: `${width}px`,
    maxHeight: `${Math.max(200, vh - VIEWPORT_MARGIN * 2)}px`,
  }

  if (!rect) return base

  const height = tooltipHeight.value
  const left = clamp(
    rect.x + rect.width / 2 - width / 2,
    VIEWPORT_MARGIN,
    Math.max(VIEWPORT_MARGIN, vw - width - VIEWPORT_MARGIN),
  )
  const below = rect.y + rect.height + PADDING + GAP
  const above = rect.y - PADDING - GAP - height

  if (vh - below - VIEWPORT_MARGIN >= height) {
    return { ...base, position: 'fixed', top: `${below}px`, left: `${left}px` }
  }
  if (above >= VIEWPORT_MARGIN) {
    return { ...base, position: 'fixed', top: `${above}px`, left: `${left}px` }
  }

  const spaceRight = vw - (rect.x + rect.width + PADDING + GAP) - VIEWPORT_MARGIN
  const spaceLeft = rect.x - PADDING - GAP - VIEWPORT_MARGIN
  const verticalTop = clamp(
    rect.y + rect.height / 2 - height / 2,
    VIEWPORT_MARGIN,
    Math.max(VIEWPORT_MARGIN, vh - height - VIEWPORT_MARGIN),
  )

  if (spaceRight >= width) {
    return {
      ...base,
      position: 'fixed',
      top: `${verticalTop}px`,
      left: `${rect.x + rect.width + PADDING + GAP}px`,
    }
  }
  if (spaceLeft >= width) {
    return {
      ...base,
      position: 'fixed',
      top: `${verticalTop}px`,
      left: `${rect.x - PADDING - GAP - width}px`,
    }
  }

  const fallbackTop = clamp(
    vh - below >= rect.y ? below : above,
    VIEWPORT_MARGIN,
    Math.max(VIEWPORT_MARGIN, vh - height - VIEWPORT_MARGIN),
  )
  return { ...base, position: 'fixed', top: `${fallbackTop}px`, left: `${left}px` }
})

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

function rectOf(el: Element): HighlightRect {
  const r = el.getBoundingClientRect()
  return { x: r.left, y: r.top, width: r.width, height: r.height }
}

function sameRect(a: HighlightRect | null, b: HighlightRect) {
  return !!a && a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height
}

function clearHighlight() {
  stopTracking()
  targetObserver.disconnect()
  if (highlightedEl) {
    highlightedEl.classList.remove('ob-highlighted')
    highlightedEl = null
  }
  highlightRect.value = null
}

function updateRect(el: Element) {
  if (highlightedEl && highlightedEl !== el) {
    highlightedEl.classList.remove('ob-highlighted')
    targetObserver.disconnect()
  }
  highlightedEl = el
  el.classList.add('ob-highlighted')
  targetObserver.observe(el)
  highlightRect.value = rectOf(el)
}

function syncRect() {
  if (!highlightedEl) return
  if (!highlightedEl.isConnected) {
    const step = steps[currentIndex.value]
    const replacement = step?.target
      ? document.querySelector(`[data-onboarding="${step.target}"]`)
      : null
    if (!replacement) {
      clearHighlight()
      return
    }
    updateRect(replacement)
    return
  }
  const next = rectOf(highlightedEl)
  if (!sameRect(highlightRect.value, next)) highlightRect.value = next
}

function stopTracking() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  trackDeadline = 0
}

function trackRect(duration: number) {
  trackDeadline = Math.max(trackDeadline, performance.now() + duration)
  if (rafId !== null) return
  const loop = () => {
    syncRect()
    if (highlightedEl && performance.now() < trackDeadline) {
      rafId = requestAnimationFrame(loop)
    } else {
      rafId = null
    }
  }
  rafId = requestAnimationFrame(loop)
}

function isAtLocation(location: StepLocation) {
  const current = router.currentRoute.value
  if (current.path !== location.path) return false
  return Object.entries(location.query ?? {}).every(([key, value]) => current.query[key] === value)
}

async function waitForTarget(selector: string, token: number) {
  const deadline = performance.now() + TARGET_TIMEOUT_MS
  let el = document.querySelector(selector)
  while (!el && performance.now() < deadline) {
    await sleep(TARGET_POLL_MS)
    if (token !== activationToken) return null
    el = document.querySelector(selector)
  }
  return el
}

function scrollTargetIntoView(el: Element) {
  if (!isMobile.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }
  const rect = el.getBoundingClientRect()
  const limit = viewport.value.height * MOBILE_TARGET_RATIO
  const desiredTop = Math.max(MOBILE_SAFE_TOP, limit - rect.height)
  const delta = rect.top - desiredTop
  if (Math.abs(delta) > 4) window.scrollBy({ top: delta, behavior: 'smooth' })
}

async function focusPanel() {
  await nextTick()
  const el = isModalStep.value ? cardRef.value : tooltipRef.value
  el?.focus({ preventScroll: true })
}

async function activateStep(index: number) {
  const step = steps[index]
  if (!step || !onboarding.active) return

  const token = ++activationToken

  if (step.isModal) {
    clearHighlight()
    isNavigating.value = false
    await focusPanel()
    return
  }

  isNavigating.value = true

  if (step.location && !isAtLocation(step.location)) {
    clearHighlight()
    await router.push({ path: step.location.path, query: step.location.query })
    await nextTick()
    await sleep(ROUTE_SETTLE_MS)
  } else {
    await nextTick()
  }
  if (token !== activationToken) return

  const el = step.target ? await waitForTarget(`[data-onboarding="${step.target}"]`, token) : null
  if (token !== activationToken) return

  isNavigating.value = false

  if (!el) {
    clearHighlight()
    await focusPanel()
    return
  }

  updateRect(el)
  scrollTargetIntoView(el)
  trackRect(TRACK_MS)
  await focusPanel()

  await sleep(SCROLL_SETTLE_MS)
  if (token !== activationToken) return
  syncRect()
  trackRect(TRACK_SETTLE_MS)
}

function selectStep(index: number) {
  if (index === currentIndex.value) return
  currentIndex.value = index
}

function next() {
  if (isLast.value) {
    complete()
    return
  }
  currentIndex.value += 1
}

function prev() {
  if (isFirst.value) return
  currentIndex.value -= 1
}

function complete() {
  onboarding.finish()
  router.push('/')
}

function skip() {
  onboarding.finish()
}

function close() {
  onboarding.finish()
}

function dismiss() {
  paused.value = true
  onboarding.pause()
}

function resume() {
  onboarding.start()
}

function hideResume() {
  paused.value = false
}

function nudge() {
  if (nudgeTimer) clearTimeout(nudgeTimer)
  nudging.value = true
  nudgeTimer = setTimeout(() => {
    nudging.value = false
    nudgeTimer = null
  }, NUDGE_MS)
}

function handleKeydown(e: KeyboardEvent) {
  if (!onboarding.active) return
  if (e.key === 'Escape') {
    e.preventDefault()
    dismiss()
  }
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
}

function handleViewportChange() {
  viewport.value = { width: window.innerWidth, height: window.innerHeight }
  syncRect()
}

watch(tooltipRef, (el) => {
  tooltipObserver.disconnect()
  if (!el) return
  tooltipHeight.value = el.offsetHeight
  tooltipObserver.observe(el)
})

watch(
  () => onboarding.active,
  (val) => {
    if (val) {
      paused.value = false
      activateStep(currentIndex.value)
    } else {
      activationToken += 1
      isNavigating.value = false
      clearHighlight()
    }
  },
  { immediate: true },
)

watch(currentIndex, (idx) => activateStep(idx))

onMounted(() => {
  window.addEventListener('scroll', syncRect, true)
  window.addEventListener('resize', handleViewportChange)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('scroll', syncRect, true)
  window.removeEventListener('resize', handleViewportChange)
  document.removeEventListener('keydown', handleKeydown)
  if (nudgeTimer) clearTimeout(nudgeTimer)
  tooltipObserver.disconnect()
  clearHighlight()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="ob-overlay">
      <div
        v-if="onboarding.active && isModalStep"
        class="ob-overlay"
        @click.self="nudge"
      >
        <div
          ref="card"
          class="ob-card"
          :class="{ 'ob-nudge': nudging }"
          role="dialog"
          aria-modal="true"
          tabindex="-1"
          :aria-label="currentStep.title"
        >
          <button class="ob-close" aria-label="Close guide" @click="close">
            <PhX :size="18" weight="bold" />
          </button>

          <div class="ob-badge">{{ badgeLabel }}</div>

          <div class="ob-icon-wrap" :class="{ 'ob-icon-wrap--success': isLast }">
            <component :is="currentStep.icon" :size="40" weight="duotone" />
          </div>

          <h2 class="ob-title">{{ currentStep.title }}</h2>
          <p class="ob-description">{{ currentStep.description }}</p>

          <div class="ob-tip">
            <span class="ob-tip-label">Quick tip</span>
            <p class="ob-tip-text">{{ currentStep.tip }}</p>
          </div>

          <div class="ob-dots" role="tablist" aria-label="Guide progress">
            <button
              v-for="(step, i) in steps"
              :key="step.title"
              class="ob-dot"
              :class="{ 'ob-dot--active': i === currentIndex }"
              role="tab"
              type="button"
              :aria-selected="i === currentIndex"
              :aria-label="`Go to step ${i + 1}: ${step.title}`"
              @click="selectStep(i)"
            />
          </div>

          <div class="ob-actions">
            <button type="button" class="btn btn-secondary btn-sm ob-skip" @click="skip">Skip</button>
            <div class="ob-nav-btns">
              <button v-if="!isFirst" type="button" class="btn btn-secondary btn-sm" @click="prev">
                Previous
              </button>
              <button type="button" class="btn btn-primary btn-sm" @click="next">
                {{ isLast ? 'Done' : 'Get Started' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <template v-if="onboarding.active && !isModalStep">
      <svg
        v-if="highlightRect"
        class="ob-spotlight-svg"
        aria-hidden="true"
        @click="nudge"
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

      <div v-else class="ob-spotlight-plain" aria-hidden="true" @click="nudge" />

      <Transition name="ob-tooltip-fade" appear>
        <div
          ref="tooltip"
          class="ob-tooltip"
          :class="{ 'ob-tooltip--centered': !highlightRect, 'ob-nudge': nudging }"
          :style="tooltipStyle"
          role="dialog"
          aria-modal="true"
          tabindex="-1"
          :aria-label="currentStep.title"
        >
          <button class="ob-close ob-close--inline" aria-label="Close guide" @click="close">
            <PhX :size="16" weight="bold" />
          </button>

          <div class="ob-badge ob-badge--sm">{{ badgeLabel }}</div>

          <div class="ob-tooltip-header">
            <div class="ob-tooltip-icon">
              <component :is="currentStep.icon" :size="28" weight="duotone" />
            </div>
            <h3 class="ob-tooltip-title">{{ currentStep.title }}</h3>
          </div>

          <p class="ob-tooltip-desc">{{ currentStep.description }}</p>

          <div class="ob-tip ob-tip--compact">
            <span class="ob-tip-label">Tip</span>
            <p class="ob-tip-text">{{ currentStep.tip }}</p>
          </div>

          <p v-if="isNavigating" class="ob-status" role="status">Looking for it on the page…</p>

          <div class="ob-dots" role="tablist" aria-label="Guide progress">
            <button
              v-for="(step, i) in steps"
              :key="step.title"
              class="ob-dot"
              :class="{ 'ob-dot--active': i === currentIndex }"
              role="tab"
              type="button"
              :aria-selected="i === currentIndex"
              :aria-label="`Go to step ${i + 1}: ${step.title}`"
              @click="selectStep(i)"
            />
          </div>

          <div class="ob-actions">
            <button type="button" class="btn btn-secondary btn-sm ob-skip" @click="skip">Skip</button>
            <div class="ob-nav-btns">
              <button v-if="!isFirst" type="button" class="btn btn-secondary btn-sm" @click="prev">
                Previous
              </button>
              <button type="button" class="btn btn-primary btn-sm" @click="next">Next</button>
            </div>
          </div>
        </div>
      </Transition>
    </template>

    <Transition name="ob-tooltip-fade">
      <div v-if="paused && !onboarding.active" class="ob-resume" role="region" aria-label="Onboarding guide paused">
        <span class="ob-resume-text">Guide paused</span>
        <button type="button" class="btn btn-primary btn-sm" @click="resume">Resume</button>
        <button
          type="button"
          class="ob-close ob-close--pill"
          aria-label="Hide the paused guide reminder"
          @click="hideResume"
        >
          <PhX :size="14" weight="bold" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
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

.ob-card:focus,
.ob-tooltip:focus {
  outline: none;
}

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

@media (hover: hover) {
  .ob-close:hover {
    background: rgba(0, 0, 0, 0.07);
    color: var(--text-primary);
  }
}

@media (hover: hover) {
  [data-theme="dark"] .ob-close:hover {
    background: rgba(255, 255, 255, 0.09);
  }
}

.ob-close--inline {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
}

.ob-close--pill {
  position: static;
  width: 26px;
  height: 26px;
}

.ob-resume {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 402;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.ob-resume-text {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-secondary);
}

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

.ob-status {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 0 0 12px;
}

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

@media (hover: hover) {
  .ob-dot:hover:not(.ob-dot--active) {
    background: rgba(var(--color-accent-rgb), 0.40);
    transform: scale(1.2);
  }
}

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

.ob-spotlight-svg {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 400;
  pointer-events: all;
  cursor: default;
}

.ob-spotlight-plain {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 400;
  pointer-events: all;
}

.ob-tooltip {
  position: fixed;
  z-index: 401;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  transition: top 0.26s var(--ease-smooth), left 0.26s var(--ease-smooth);
}

.ob-tooltip--centered {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: none;
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

.ob-overlay-enter-active { transition: opacity 0.22s ease; }
.ob-overlay-leave-active { transition: opacity 0.18s ease; }
.ob-overlay-enter-from,
.ob-overlay-leave-to { opacity: 0; }

.ob-tooltip-fade-enter-active { transition: opacity 0.2s ease; }
.ob-tooltip-fade-leave-active { transition: opacity 0.15s ease; }
.ob-tooltip-fade-enter-from,
.ob-tooltip-fade-leave-to { opacity: 0; }

@keyframes ob-nudge-shake {
  0%, 100% { transform: translateX(0); }
  20%      { transform: translateX(-5px); }
  45%      { transform: translateX(5px); }
  70%      { transform: translateX(-3px); }
}

@keyframes ob-nudge-shake-centered {
  0%, 100% { transform: translate(-50%, -50%); }
  20%      { transform: translate(calc(-50% - 5px), -50%); }
  45%      { transform: translate(calc(-50% + 5px), -50%); }
  70%      { transform: translate(calc(-50% - 3px), -50%); }
}

.ob-nudge {
  animation: ob-nudge-shake 0.42s var(--ease-smooth);
}

.ob-tooltip--centered.ob-nudge {
  animation: ob-nudge-shake-centered 0.42s var(--ease-smooth);
}

@media (prefers-reduced-motion: reduce) {
  .ob-tooltip { transition: none; }
  .ob-nudge,
  .ob-tooltip--centered.ob-nudge { animation: none; }
}

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

  .ob-tooltip,
  .ob-tooltip--centered {
    border-radius: 16px 16px 0 0 !important;
    top: auto !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    max-height: 58vh !important;
    transform: none !important;
    transition: none;
  }

  .ob-tooltip--centered.ob-nudge,
  .ob-nudge {
    animation: none;
  }

  .ob-resume {
    right: 16px;
    left: 16px;
    bottom: 16px;
    justify-content: space-between;
  }
}
</style>
