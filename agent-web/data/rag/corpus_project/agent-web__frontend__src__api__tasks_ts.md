<!-- source: agent-web/frontend/src/api/tasks.ts | title: tasks.ts -->

import { api } from './client'

export interface TaskStatus {
  task_id: string
  stage: string
  request: string
  plan?: string
  execution_result?: string
  validation_result?: string
  done: boolean
  paused: boolean
  error?: string | null
  log_count?: number
}


export async function createTask(request: string, model?: string, profile_content?: string): Promise<{ task_id: string; stage: string; request: string }> {
  const r = await api('/tasks', {
    method: 'POST',
    body: JSON.stringify({ request, model: model ?? '', profile_content: profile_content ?? '' }),
  })
  return r.json()
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  const r = await api(`/tasks/${taskId}`)
  return r.json()
}

export async function listTasks(): Promise<TaskStatus[]> {
  const r = await api('/tasks')
  return r.json()
}

export async function sendFeedback(taskId: string, action: 'continue' | 'pause' | 'feedback', text = ''): Promise<void> {
  await api(`/tasks/${taskId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ action, text }),
  })
}

export function streamTask(taskId: string, onMessage: (msg: TaskMessage) => void, onDone?: () => void): () => void {
  const es = new EventSource(`/api/tasks/${taskId}/stream`)
  es.onmessage = (e) => {
    try {
      const msg: TaskMessage = JSON.parse(e.data)
      onMessage(msg)
      if (msg.type === 'done' || msg.type === 'error') {
        es.close()
        onDone?.()
      }
    } catch { /* ignore parse errors */ }
  }
  es.onerror = () => {
    es.close()
    onDone?.()
  }
  return () => es.close()
}

export interface TaskMessage {
  type: 'output' | 'confirm' | 'done' | 'error' | 'ping'
  text?: string
  prompt?: string
  stage?: string
  task?: Record<string, unknown>
}
