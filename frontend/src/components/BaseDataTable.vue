<script setup lang="ts">
import BaseCard from './BaseCard.vue'

const SKELETON_WIDTHS = [62, 78, 55, 85, 70]

defineProps<{
  loading: boolean
  empty: boolean
  emptyMessage?: string
  title?: string
  columns?: number
}>()
</script>

<template>
  <BaseCard :title="title" flush>
    <template v-if="$slots.actions" #actions>
      <slot name="actions" />
    </template>
    <div style="overflow-x: auto;">
      <table class="data-table">
        <thead><slot name="head" /></thead>

        <tbody v-if="loading">
          <tr v-for="i in 5" :key="i" class="skeleton-tr">
            <td v-for="j in (columns ?? 5)" :key="j">
              <div
                class="skeleton-cell"
                :style="{ width: SKELETON_WIDTHS[(i + j) % SKELETON_WIDTHS.length] + '%' }"
              />
            </td>
          </tr>
        </tbody>

        <tbody v-else-if="empty">
          <tr>
            <td colspan="99" class="table-empty-cell">
              <div class="table-empty">
                <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m2.25-2.25h-2.25m0 0h-7.5m7.5 0v1.5" />
                </svg>
                <p class="table-empty-msg">{{ emptyMessage ?? 'No items yet.' }}</p>
              </div>
            </td>
          </tr>
        </tbody>

        <tbody v-else>
          <slot name="body" />
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>
