export interface FeaturedCompanySortKey {
  tier: 'big' | 'mid' | 'small'
  deadlineDays: number | null
  jobCount: number
}

const TIER_WEIGHT = { big: 3, mid: 2, small: 1 } as const

export function compareFeaturedCompanies(
  a: FeaturedCompanySortKey,
  b: FeaturedCompanySortKey,
): number {
  const tierDifference = TIER_WEIGHT[b.tier] - TIER_WEIGHT[a.tier]
  if (tierDifference !== 0) return tierDifference

  if (a.deadlineDays === null) return b.deadlineDays === null ? b.jobCount - a.jobCount : 1
  if (b.deadlineDays === null) return -1

  const deadlineDifference = a.deadlineDays - b.deadlineDays
  return deadlineDifference !== 0 ? deadlineDifference : b.jobCount - a.jobCount
}
