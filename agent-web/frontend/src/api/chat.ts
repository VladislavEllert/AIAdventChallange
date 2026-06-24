const BASE = '/api'

export interface ChatUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost_rub: number
  elapsed_ms: number
}

export interface ChatCallbacks {
  onChunk: (text: string) => void
  onUsage: (u: ChatUsage) => void
  onViolation?: (inv: string, desc: string) => void
  onToolStart?: (name: string, label: string) => void
  onToolDone?: (name: string) => void
  onDone: () => void
  onError: (e: Error) => void
}

export async function streamChat(
  session_id: string,
  message: string,
  callbacks: ChatCallbacks,
  image_b64?: string,
  persona?: string,
  model?: string,
  profile_name?: string,
): Promise<void> {
  const resp = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, message, image_b64, persona, model, profile_name }),
  })

  if (!resp.ok || !resp.body) {
    callbacks.onError(new Error(`HTTP ${resp.status}`))
    return
  }

  const reader = resp.body.getReader()
  const dec = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })

    const lines = buf.split('\n')
    buf = lines.pop() ?? ''

    let event = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        event = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (event === 'chunk') callbacks.onChunk(data.text)
          else if (event === 'usage') callbacks.onUsage(data)
          else if (event === 'violation') callbacks.onViolation?.(data.invariant ?? '', data.description ?? '')
          else if (event === 'tool_start') callbacks.onToolStart?.(data.name ?? '', data.label ?? '')
          else if (event === 'tool_done') callbacks.onToolDone?.(data.name ?? '')
          else if (event === 'done') callbacks.onDone()
        } catch {}
        event = ''
      }
    }
  }
}
