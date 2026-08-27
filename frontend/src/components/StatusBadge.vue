<template>
  <span class="status-badge" :class="statusClass">
    <span v-if="isPending" class="spinner" aria-hidden="true"></span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isPendingSubmissionStatus, submissionStatusClass } from '../submissionStatus'
import type { SubmissionStatus } from '../types'

const props = defineProps<{ status: SubmissionStatus }>()

const LABELS: Record<SubmissionStatus, string> = {
  pending: '排队中',
  judging: '评测中',
  AC: '通过',
  WA: '答案错误',
  TLE: '超出时间限制',
  MLE: '超出内存限制',
  CE: '编译错误',
  RE: '运行错误',
  IE: '系统错误',
}

const label = computed(() => LABELS[props.status] ?? props.status)
const statusClass = computed(() => submissionStatusClass(props.status))
const isPending = computed(() => isPendingSubmissionStatus(props.status))
</script>
