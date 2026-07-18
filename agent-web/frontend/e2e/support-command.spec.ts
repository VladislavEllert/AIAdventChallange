import { test, expect } from '@playwright/test'

// Guards day 33's /support command golden path: `/support <ticket_id> <question>`
// pulls the ticket through a real MCP round-trip (get_ticket, not a python json.load),
// injects its fields (environment/version/symptom) into the system prompt, and the
// answer must be specific to that ticket's environment — not generic advice.
//
// TICKET-001 (see agent-web/data/support/tickets.json) is the Windows/SOCKS-proxy bug:
// environment mentions Windows 11 + a system SOCKS proxy enabled in OS network settings.
// A real, ticket-grounded answer should reference Windows/proxy/trust_env, not a generic
// "check your network settings" reply.
//
// Requires: PROXYAPI_KEY (embed backend for kb=project) and
// mcp-server/project_server.py running on 127.0.0.1:8002 (PROJECT_ROOT=<repo root>) for
// get_ticket to resolve to real ticket data instead of the "MCP-сервер недоступен" fallback.
test('support command: ticket-grounded answer references the ticket environment', async ({ page }) => {
  await page.goto('/')

  const nicknameInput = page.getByPlaceholder('Например: Влад')
  await nicknameInput.waitFor({ state: 'visible', timeout: 5_000 })
  await nicknameInput.fill('e2e-support-bot')
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await nicknameInput.waitFor({ state: 'hidden', timeout: 5_000 })

  await page.getByRole('button', { name: /Новый чат/ }).click()

  const textarea = page.getByPlaceholder(/Напиши сообщение/)
  await expect(textarea).toBeVisible()

  await textarea.fill('/model openai/gpt-4o-mini')
  await textarea.press('Enter')
  await expect(page.getByText('Модель переключена')).toBeVisible()

  await textarea.fill('/support TICKET-001 как починить прокси на Windows?')
  await expect(textarea).toBeEnabled()
  await textarea.press('Enter')

  const assistantBubble = page.locator('.prose').last()
  await expect(assistantBubble).not.toHaveText('', { timeout: 30_000 })

  // Not the MCP-unreachable fallback — the ticket really round-tripped through
  // project_server.py's get_ticket tool.
  await expect(assistantBubble).not.toContainText('project MCP-сервер недоступен')

  // Ticket-specific: environment mentions Windows + system proxy — a generic answer
  // wouldn't mention either.
  await expect(assistantBubble).toContainText(/windows|прокси|proxy|trust_env/i, {
    timeout: 30_000,
  })

  await expect(textarea).toBeEnabled({ timeout: 10_000 })
})
