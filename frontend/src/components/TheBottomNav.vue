<script setup lang="ts">
import { PhChartBar, PhArrowsLeftRight, PhWallet, PhReceipt, PhGear } from '@phosphor-icons/vue'
</script>

<template>
  <nav class="bottom-nav">
    <RouterLink to="/" class="bottom-nav-item">
      <PhChartBar weight="duotone" :size="22" />
      <span>Dashboard</span>
    </RouterLink>
    <RouterLink to="/transactions" class="bottom-nav-item">
      <PhArrowsLeftRight weight="duotone" :size="22" />
      <span>Income</span>
    </RouterLink>
    <RouterLink to="/balance-snapshots" class="bottom-nav-item">
      <PhWallet weight="duotone" :size="22" />
      <span>Balances</span>
    </RouterLink>
    <RouterLink to="/expenses" class="bottom-nav-item">
      <PhReceipt weight="duotone" :size="22" />
      <span>Expenses</span>
    </RouterLink>
    <RouterLink to="/settings" class="bottom-nav-item">
      <PhGear weight="duotone" :size="22" />
      <span>Settings</span>
    </RouterLink>
  </nav>
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
    background: #ffffff;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 20px 20px 0 0;
    box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
}

.bottom-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: rgba(0, 0, 0, 0.45);
  font-size: 0.625rem;
  font-weight: 500;
  font-family: var(--font-body);
  transition: color 0.15s;
}

.bottom-nav-item.router-link-exact-active {
  color: var(--color-accent);
  font-weight: 600;
}
</style>
