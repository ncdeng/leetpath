export interface TabsScrollMetrics {
  scrollLeft: number
  clientWidth: number
  scrollWidth: number
}

export interface TabsFadeState {
  left: boolean
  right: boolean
}

export function shouldAutoShowPopupOnce(lastShownDate: string | null, today: string): boolean {
  return lastShownDate !== today
}

export function tabsFadeState(
  { scrollLeft, clientWidth, scrollWidth }: TabsScrollMetrics,
  threshold = 4,
): TabsFadeState {
  return {
    left: scrollLeft > threshold,
    right: scrollLeft + clientWidth < scrollWidth - threshold,
  }
}
