interface ClipboardTextArea {
  value: string
  style: { position: string; opacity: string }
  select(): void
  remove(): void
}

export interface ClipboardEnvironment {
  navigator: {
    clipboard?: { writeText(text: string): Promise<void> }
  }
  document: {
    body: { appendChild(node: ClipboardTextArea): unknown }
    createElement(tagName: string): ClipboardTextArea
    execCommand(command: string): boolean
  }
}

export async function copyToClipboard(
  text: string,
  environment?: ClipboardEnvironment,
): Promise<boolean> {
  const activeEnvironment = environment ?? {
    navigator: globalThis.navigator,
    document: globalThis.document,
  } as ClipboardEnvironment

  try {
    await activeEnvironment.navigator.clipboard?.writeText(text)
    if (activeEnvironment.navigator.clipboard) return true
  } catch {
    // Fall back for denied or unavailable Clipboard API access.
  }

  let textarea: ClipboardTextArea | undefined
  try {
    textarea = activeEnvironment.document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    activeEnvironment.document.body.appendChild(textarea)
    textarea.select()
    return activeEnvironment.document.execCommand('copy')
  } catch {
    return false
  } finally {
    textarea?.remove()
  }
}
