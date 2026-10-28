<script setup>
import AppIcon from '@/components/AppIcon'

defineProps({
  title: { type: String, required: true },
})
</script>

<template>
  <main class="auth-page">
    <section class="auth-card" aria-labelledby="auth-title">
      <div class="auth-brand">
        <span class="app-brand-mark"><AppIcon name="coffee" :size="22" /></span>
        <div>
          <p class="auth-app-name">Two Beans App</p>
          <p class="auth-subtitle">Inventaris Two Beans Coffee</p>
        </div>
      </div>
      <h1 id="auth-title" class="auth-title">{{ title }}</h1>
      <slot />
    </section>
  </main>
</template>
