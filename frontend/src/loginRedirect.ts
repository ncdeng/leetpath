export interface RedirectLocation {
  pathname: string
  search: string
  hash: string
}

export function loginRedirectUrl(currentLocation: RedirectLocation): string {
  const redirect = currentLocation.pathname + currentLocation.search + currentLocation.hash
  return `/login?redirect=${encodeURIComponent(redirect)}`
}
