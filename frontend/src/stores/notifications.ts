import { defineStore } from 'pinia'
import { ref } from 'vue'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface AppNotification {
  id: string
  type: NotificationType
  title: string
  message?: string
  action?: { label: string; handler: () => void }
  duration: number // ms; 0 = persistent
}

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<AppNotification[]>([])

  function add(notification: Omit<AppNotification, 'id'> & { id?: string }): string {
    const notifId = notification.id ?? crypto.randomUUID()
    items.value.push({ duration: 6000, ...notification, id: notifId })
    return notifId
  }

  function dismiss(notifId: string) {
    items.value = items.value.filter((n) => n.id !== notifId)
  }

  return { items, add, dismiss }
})
