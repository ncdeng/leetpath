// 剪贴板工具：navigator.clipboard 在非 HTTPS 或权限被拒时会 reject，
// 统一回退 execCommand，并把成败如实返回给调用方，避免「复制失败却提示已复制」
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* 非 HTTPS / 权限拒绝，走 execCommand 回退 */
  }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    textarea.remove()
    return ok
  } catch {
    return false
  }
}
