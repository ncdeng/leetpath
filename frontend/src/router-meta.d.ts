import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    admin?: boolean
    hasInlineAi?: boolean
  }
}
