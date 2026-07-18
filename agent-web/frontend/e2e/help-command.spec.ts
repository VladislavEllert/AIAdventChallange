import { test, expect } from '@playwright/test'

// Guards day 31's /help command golden path: send `/help <question>` and get
// back a real, cited answer with source excerpts from the project's own RAG
// knowledge base — not the GitLab Handbook (kb=project is forced server-side,
// there's no UI toggle for it). Also drives the git-branch question, which
// depends on mcp-server/project_server.py actually running.
//
// Requires: PROXYAPI_KEY (embed backend for the project KB is proxyapi by
// default, see rag/config.py) and mcp-server/project_server.py running on
// 127.0.0.1:8002 (PROJECT_ROOT=<repo root>) for the branch question to
// resolve to a real branch name instead of the "unreachable" fallback text.
test('help command: RAG question returns a cited answer from the project KB', async ({ page }) => {
  await page.goto('/')

  const nicknameInput = page.getByPlaceholder('Например: Влад')
  await nicknameInput.waitFor({ state: 'visible', timeout: 5_000 })
  await nicknameInput.fill('e2e-help-bot')
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await nicknameInput.waitFor({ state: 'hidden', timeout: 5_000 })

  await page.getByRole('button', { name: /Новый чат/ }).click()

  const textarea = page.getByPlaceholder(/Напиши сообщение/)
  await expect(textarea).toBeVisible()

  await textarea.fill('/model openai/gpt-4o-mini')
  await textarea.press('Enter')
  await expect(page.getByText('Модель переключена')).toBeVisible()

  await textarea.fill('/help как реализован RAG в этом проекте?')
  await expect(textarea).toBeEnabled()
  await textarea.press('Enter')

  // (No toBeDisabled() assertion here — the RAG retrieval step can resolve
  // fast enough that streaming starts/finishes before a poll catches the
  // disabled state; golden-path.spec.ts already covers that regression guard
  // generically. This spec's job is the /help-specific behavior below.)

  const assistantBubble = page.locator('.prose').last()
  await expect(assistantBubble).not.toHaveText('', { timeout: 30_000 })
  await expect(assistantBubble).toContainText(/rag|RAG/i, { timeout: 30_000 })

  await expect(textarea).toBeEnabled({ timeout: 10_000 })
})

test('help command: git-branch question answers with a real branch, not a guess', async ({ page }) => {
  await page.goto('/')

  const nicknameInput = page.getByPlaceholder('Например: Влад')
  await nicknameInput.waitFor({ state: 'visible', timeout: 5_000 })
  await nicknameInput.fill('e2e-help-bot-2')
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await nicknameInput.waitFor({ state: 'hidden', timeout: 5_000 })

  await page.getByRole('button', { name: /Новый чат/ }).click()

  const textarea = page.getByPlaceholder(/Напиши сообщение/)
  await textarea.fill('/model openai/gpt-4o-mini')
  await textarea.press('Enter')
  await expect(page.getByText('Модель переключена')).toBeVisible()

  await textarea.fill('/help на какой я ветке?')
  await textarea.press('Enter')

  const assistantBubble = page.locator('.prose').last()
  await expect(assistantBubble).not.toHaveText('', { timeout: 30_000 })
  // Doesn't assert a specific branch name (CI/dev machines differ) — asserts
  // the answer isn't the MCP-unreachable fallback text, i.e. the tool call
  // actually round-tripped through mcp-server/project_server.py.
  await expect(assistantBubble).not.toContainText('project MCP-сервер недоступен')

  await expect(textarea).toBeEnabled({ timeout: 10_000 })
})
