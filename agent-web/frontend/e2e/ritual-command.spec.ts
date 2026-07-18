import { test, expect } from '@playwright/test'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../../..')

// Day 35: /ritual chat command, driven live in a real browser against a real
// backend + real ProxyAPI. Two scenarios, mirroring day 34's tool-confirm.spec.ts
// shape:
//  (a) --dry-run: draft row + verifier result + patch diff all render in chat,
//      no confirm modal (nothing is ever written in dry-run mode).
//  (b) real (non-dry-run) run against a throwaway day number ("90", which will
//      never collide with a real course day): the confirm modal appears for
//      write_file (day 34's SAME modal, day 35 adds no new frontend component
//      — see week-07/day-35/README.md) -> Deny -> repo stays untouched.
//
// The ACTUAL real day-35 commit (README.md + memory-bank/progress.md, day
// "35") is deliberately NOT done by clicking Allow in this automated spec —
// see week-07/day-35/README.md's "why the live commit isn't in Playwright"
// note: committing the project's own living docs from an unattended browser
// script on every CI re-run is the wrong mechanism for a one-time reviewed
// action. That commit was done via the headless CLI
// (`python -m agent_web.services.rituals.day_report 35`) after a human
// (the agent building this phase) read the printed diff and approved it —
// this spec only proves the chat UI wiring (diff renders, modal appears,
// Deny leaves disk untouched), same bar day 34's negative scenario set.

function gitStatusPorcelain(pathspec: string): string {
  return execSync(`git status --porcelain -- ${pathspec}`, { cwd: REPO_ROOT }).toString().trim()
}

async function startNewChat(page: import('@playwright/test').Page, nickname: string) {
  await page.goto('/')
  const nicknameInput = page.getByPlaceholder('Например: Влад')
  await nicknameInput.waitFor({ state: 'visible', timeout: 5_000 })
  await nicknameInput.fill(nickname)
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await nicknameInput.waitFor({ state: 'hidden', timeout: 5_000 })

  await page.getByRole('button', { name: /Новый чат/ }).click()

  const textarea = page.getByPlaceholder(/Напиши сообщение/)
  await expect(textarea).toBeVisible()
  await textarea.fill('/model openai/gpt-4o-mini')
  await textarea.press('Enter')
  await expect(page.getByText('Модель переключена')).toBeVisible()
  return textarea
}

test.describe('day 35: /ritual', () => {
  test('dry-run: draft + verifier + patch diff render, no confirm modal', async ({ page }) => {
    test.setTimeout(120_000)
    const textarea = await startNewChat(page, 'e2e-ritual-dryrun')

    await textarea.fill('/ritual day 90 --dry-run')
    await expect(textarea).toBeEnabled()
    await textarea.press('Enter')
    await expect(textarea).toBeDisabled()

    const assistantBubble = page.locator('.prose').last()
    await expect(assistantBubble).not.toHaveText('', { timeout: 100_000 })
    await expect(textarea).toBeEnabled({ timeout: 100_000 })

    await expect(page.getByText('Черновик строки')).toBeVisible()
    // Either the verifier approved (patch diff shown, "--dry-run" note) or
    // rejected (rejection message) — both are valid live-LLM outcomes; what
    // matters is nothing ever prompts for confirmation in dry-run mode.
    await expect(page.getByText('Подтверди опасную операцию')).toHaveCount(0)

    await page.screenshot({ path: '../../week-07/day-35/screens/day35-ritual-dry-run.png', fullPage: true })
  })

  test('real run, throwaway day: confirm modal appears, Deny leaves repo untouched', async ({ page }) => {
    test.setTimeout(180_000)
    const readmeBefore = gitStatusPorcelain('README.md')
    const progressBefore = gitStatusPorcelain('memory-bank/progress.md')

    const textarea = await startNewChat(page, 'e2e-ritual-deny')

    await textarea.fill('/ritual day 90')
    await expect(textarea).toBeEnabled()
    await textarea.press('Enter')

    const modalTitle = page.getByText('Подтверди опасную операцию')
    await modalTitle.waitFor({ state: 'visible', timeout: 150_000 })
    await expect(page.getByText('write_file', { exact: true })).toBeVisible()

    await page.screenshot({ path: '../../week-07/day-35/screens/day35-ritual-confirm-modal.png', fullPage: true })

    await page.getByRole('button', { name: /Отклонить/ }).click()
    await modalTitle.waitFor({ state: 'hidden', timeout: 10_000 })

    await expect(textarea).toBeEnabled({ timeout: 100_000 })

    // Negative case, mandatory: nothing written to disk — same invariant
    // day 34's tool-confirm.spec.ts proves for write_file/delete_file.
    expect(gitStatusPorcelain('README.md')).toBe(readmeBefore)
    expect(gitStatusPorcelain('memory-bank/progress.md')).toBe(progressBefore)

    await page.screenshot({ path: '../../week-07/day-35/screens/day35-ritual-deny-clean.png', fullPage: true })
  })
})
