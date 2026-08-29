<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- 导航 -->
    <template v-if="name === 'palette'"><path d="M12 22a10 10 0 1 1 10-10c0 4.9-3.6 5-6 5h-1.2a2.3 2.3 0 0 0-1.8 3.7c.4.5.3 1.3-.4 1.3Z" /><circle cx="7.6" cy="10.4" r="1.1" fill="currentColor" stroke="none" /><circle cx="12" cy="7.6" r="1.1" fill="currentColor" stroke="none" /><circle cx="16.4" cy="10.4" r="1.1" fill="currentColor" stroke="none" /></template>
    <template v-else-if="name === 'home'"><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /><path d="M9 21v-6h6v6" /></template>
    <template v-else-if="name === 'trophy'"><path d="M8 21h8M12 17v4" /><path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" /><path d="M7 6H4a2 2 0 0 0 2 4h1M17 6h3a2 2 0 0 1-2 4h-1" /></template>
    <template v-else-if="name === 'list'"><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" /></template>
    <template v-else-if="name === 'pencil'"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z" /></template>
    <template v-else-if="name === 'cards'"><rect x="3" y="6" width="13" height="15" rx="2" /><path d="M8 6V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-2" transform="translate(0 1)" /></template>
    <template v-else-if="name === 'book'"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15Z" /><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5" /></template>
    <template v-else-if="name === 'briefcase'"><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></template>
    <template v-else-if="name === 'link'"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></template>
    <template v-else-if="name === 'gear'"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" /></template>
    <!-- 主题 -->
    <template v-else-if="name === 'sun'"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></template>
    <template v-else-if="name === 'moon'"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" /></template>
    <template v-else-if="name === 'leaf'"><path d="M11 20A7 7 0 0 1 4 13c0-4 3-8 9-10 4-1.4 7-1 7-1s.5 3-1 7c-2 6-5 9-8 11Z" /><path d="M4 21c4-6 8-9 12-11" /></template>
    <template v-else-if="name === 'sparkle' || name === 'sparkles'"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /><path d="M19 3v4M17 5h4" /><path d="M5 19v2M4 20h2" /></template>
    <template v-else-if="name === 'shield'"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></template>
    <template v-else-if="name === 'robot'"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /><path d="M19 3v4M17 5h4" /></template>
    <!-- 通用 -->
    <template v-else-if="name === 'chevron-right'"><path d="m9 18 6-6-6-6" /></template>
    <template v-else-if="name === 'chevron-left'"><path d="m15 18-6-6 6-6" /></template>
    <template v-else-if="name === 'chevron-down'"><path d="m6 9 6 6 6-6" /></template>
    <template v-else-if="name === 'arrow-right'"><path d="M5 12h14M13 6l6 6-6 6" /></template>
    <template v-else-if="name === 'arrow-left'"><path d="M19 12H5M11 18l-6-6 6-6" /></template>
    <template v-else-if="name === 'search'"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></template>
    <template v-else-if="name === 'clock'"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></template>
    <template v-else-if="name === 'x'"><path d="M18 6 6 18M6 6l12 12" /></template>
    <template v-else-if="name === 'plus'"><path d="M12 5v14M5 12h14" /></template>
    <template v-else-if="name === 'check'"><path d="M20 6 9 17l-5-5" /></template>
    <template v-else-if="name === 'refresh'"><path d="M21 12a9 9 0 1 1-2.64-6.36L21 8" /><path d="M21 3v5h-5" /></template>
    <template v-else-if="name === 'eye'"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></template>
    <template v-else-if="name === 'eye-off'"><path d="M9.9 4.24A9.5 9.5 0 0 1 12 4c6.5 0 10 8 10 8a17 17 0 0 1-2.16 3.19M6.61 6.61A16.6 16.6 0 0 0 2 12s3.5 8 10 8a9.7 9.7 0 0 0 5.39-1.61" /><path d="m2 2 20 20" /><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" /></template>
    <template v-else-if="name === 'copy'"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></template>
    <template v-else-if="name === 'play'"><path d="m6 4 14 8-14 8V4Z" /></template>
    <template v-else-if="name === 'send'"><path d="m22 2-7 20-4-9-9-4 20-7Z" /><path d="M22 2 11 13" /></template>
    <template v-else-if="name === 'flame' || name === 'fire'"><path d="M12 22c4.4 0 7-2.8 7-6.5 0-3-2-5-3.5-7C14 6.5 13 4.5 13 2c-3 2-5 4.5-5 8 0 1 .1 2 .5 3C7.5 12 6 11 6 9c-1.2 1.8-1 4-.9 5.1C5.6 18.5 8 22 12 22Z" /></template>
    <template v-else-if="name === 'dice'"><rect x="3" y="3" width="18" height="18" rx="4" /><circle cx="8.5" cy="8.5" r="1.2" fill="currentColor" stroke="none" /><circle cx="15.5" cy="15.5" r="1.2" fill="currentColor" stroke="none" /><circle cx="15.5" cy="8.5" r="1.2" fill="currentColor" stroke="none" /><circle cx="8.5" cy="15.5" r="1.2" fill="currentColor" stroke="none" /></template>
    <template v-else><circle cx="12" cy="12" r="9" /></template>
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number | string; strokeWidth?: number | string }>(), {
  size: 20,
  strokeWidth: 1.8,
})
</script>
