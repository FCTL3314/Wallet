<script setup lang="ts">
import { watch } from 'vue'
import { PhInfo, PhCheckCircle, PhWarning, PhXCircle, PhX } from '@phosphor-icons/vue'
import { useNotificationsStore, type AppNotification, type NotificationType } from '../stores/notifications'

const notifications = useNotificationsStore()

const iconMap: Record<NotificationType, typeof PhInfo> = {
  info: PhInfo,
  success: PhCheckCircle,
  warning: PhWarning,
  error: PhXCircle,
}

function scheduleAutoDismiss(n: AppNotification) {
  if (n.duration > 0) {
    setTimeout(() => notifications.dismiss(n.id), n.duration)
  }
}

watch(
  () => [...notifications.items],
  (items, prev) => {
    const newItems = items.filter((n) => !prev?.some((p) => p.id === n.id))
    newItems.forEach(scheduleAutoDismiss)
  },
)
</script>

<template>
  <Teleport to="body">
    <div class="notifications-stack" aria-live="polite" aria-label="Notifications">
      <TransitionGroup name="notif">
        <div
          v-for="n in notifications.items.slice(-5)"
          :key="n.id"
          class="notif-card"
          :class="`notif-card--${n.type}`"
          role="alert"
        >
          <div class="notif-icon">
            <component :is="iconMap[n.type]" :size="20" weight="duotone" />
          </div>
          <div class="notif-body">
            <p class="notif-title">{{ n.title }}</p>
            <p v-if="n.message" class="notif-message">{{ n.message }}</p>
            <button
              v-if="n.action"
              class="notif-action"
              @click="n.action!.handler(); notifications.dismiss(n.id)"
            >
              {{ n.action.label }}
            </button>
          </div>
          <button class="notif-close" aria-label="Dismiss" @click="notifications.dismiss(n.id)">
            <PhX :size="14" weight="bold" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.notifications-stack {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 340px;
  max-width: calc(100vw - 48px);
  pointer-events: none;
}

.notif-card {
  pointer-events: all;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  box-shadow: var(--shadow-card);
}

.notif-card--info    .notif-icon { color: var(--color-accent); }
.notif-card--success .notif-icon { color: var(--color-income); }
.notif-card--warning .notif-icon { color: var(--color-warning); }
.notif-card--error   .notif-icon { color: var(--color-expense); }

.notif-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.notif-body {
  flex: 1;
  min-width: 0;
}

.notif-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 2px;
}

.notif-message {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0 0 8px;
  line-height: 1.5;
}

.notif-action {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-accent);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.notif-action:hover {
  color: var(--color-accent-light);
}

.notif-close {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--card-border);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.notif-close:hover {
  background: rgba(0, 0, 0, 0.06);
}

[data-theme="dark"] .notif-close:hover {
  background: rgba(255, 255, 255, 0.08);
}

/* Transitions */
.notif-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.notif-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
  position: absolute;
  width: 100%;
}

.notif-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.notif-leave-to {
  opacity: 0;
  transform: translateX(40px);
}

@media (max-width: 480px) {
  .notifications-stack {
    bottom: 80px;
    right: 12px;
    left: 12px;
    width: auto;
    max-width: none;
  }
}
</style>
