const BASE = '/api'

export interface ChatUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost_rub: number
  elapsed_ms: number
}

export interface ChatSource {
  source: string
  section: string
  chunk_id: string
  quote: string
  score: number
}

export interface ChatRagMeta {
  top_k_raw: number
  top_k_kept: number
  top_k_final: number
  best_score: number
  rewritten_query?: string
}

export interface ChatTaskState {
  goal: string
  clarified_facts: string[]
  constraints: string[]
}

export interface ChatCallbacks {
  onChunk: (text: string) => void
  onUsage: (u: ChatUsage) => void
  onViolation?: (inv: string, desc: string) => void
  onToolStart?: (name: string, label: string) => void
  onToolDone?: (name: string) => void
  onSources?: (sources: ChatSource[]) => void
  onRagMeta?: (meta: ChatRagMeta) => void
  onTaskState?: (ts: ChatTaskState) => void
  onImageProgress?: (pct: number) => void
  onImage?: (dataB64: string) => void
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
  signal?: AbortSignal,
  use_rag?: boolean,
  use_mcp?: boolean,
): Promise<void> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id, message, image_b64, persona, model, profile_name, use_rag, use_mcp }),
      signal,
    })
  } catch (e: unknown) {
    // Network failure before we even got a response (server down, LAN drop, ...).
    // Unhandled here previously left isStreaming stuck true forever — every
    // future send silently no-op'd until a full page reload.
    if (e instanceof Error && e.name !== 'AbortError') callbacks.onError(e)
    callbacks.onDone()
    return
  }

  if (!resp.ok || !resp.body) {
    callbacks.onError(new Error(`HTTP ${resp.status}`))
    callbacks.onDone()
    return
  }

  const reader = resp.body.getReader()
  const dec = new TextDecoder()
  let buf = ''

  try {
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
          else if (event === 'sources') callbacks.onSources?.(Array.isArray(data) ? data : [])
          else if (event === 'rag_meta') callbacks.onRagMeta?.(data)
          else if (event === 'task_state') callbacks.onTaskState?.(data)
          else if (event === 'image_progress') callbacks.onImageProgress?.(data.pct ?? 0)
          else if (event === 'image') callbacks.onImage?.(data.data_b64 ?? '')
          else if (event === 'done') callbacks.onDone()
        } catch {}
        event = ''
      }
    }
  }
  } catch (e: unknown) {
    // AbortError = user cancelled — not a real error
    if (e instanceof Error && e.name !== 'AbortError') {
      callbacks.onError(e)
    }
  } finally {
    callbacks.onDone()
  }
}
