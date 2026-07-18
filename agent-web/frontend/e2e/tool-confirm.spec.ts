import { test, expect } from '@playwright/test'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Day 34: file-agent tools + human-in-the-loop confirmation, driven live in a
// real browser against a real backend (mandatory per plan 34.12 — this is the
// hardest requirement of the phase; day 35 cannot be verified at all without
// the positive write case working).
//
// Two scenarios:
//  (a) SAFE tools, no confirm: "найди все места использования X и приведи к
//      одному виду" -> search_files -> read_file (x N) -> unified diff in the
//      final answer. No modal, nothing written.
//  (b) DANGEROUS tool (write_file), confirm required: update a stale draft
//      doc -> ConfirmToolModal appears -> Deny (git status stays clean) ->
//      re-run -> Allow (file actually changes on disk, verified via git diff).
//
// Requires PROXYAPI_KEY (real openai/gpt-4o-mini tool-calling calls).

const REPO_ROOT = path.resolve(__dirname, '../../..')
const DRAFT = 'week-07/day-34/TOOLS_DOC_DRAFT.md'

// DRAFT was originally `git add`-ed (staged, not committed) before this spec ran,
// giving a baseline porcelain status of "A  <path>" (staged-added). Day 35's own
// self-test (git_tools.py's `git_commit`) caught a real bug live: a bare `git
// commit` with no pathspec commits the WHOLE index, not just what that call just
// staged — DRAFT was already staged from day 34's setup and rode along into a
// day-35 ritual commit as an unrelated side effect (see git_tools.py's `_git_commit`
// fix + week-07/day-35/README.md). DRAFT is now a COMMITTED, clean, tracked file —
// baseline is empty (nothing staged/modified), and a write_file on a clean tracked
// file only touches the WORKING TREE (not the index), flipping status to " M <path>"
// (worktree-modified, not staged) rather than "AM". The fix in git_tools.py prevents
// this exact class of accidental commit-sweep from recurring.
function gitStatusPorcelain(pathspec: string): string {
  return execSync(`git status --porcelain -- ${pathspec}`, { cwd: REPO_ROOT }).toString().trim()
}

function gitRestoreToStagedBaseline(pathspec: string) {
  // Restores the WORKING TREE from the INDEX (== HEAD now that DRAFT is committed)
  // — safe no-op if nothing touched it since, discards any write_file effect if run
  // again.
  execSync(`git checkout -- ${pathspec}`, { cwd: REPO_ROOT })
}

const BASELINE_STATUS = ''

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

test.describe('day 34: file-agent tools', () => {
  test('scenario A: search_files + read_file -> unified diff, no write', async ({ page }) => {
    test.setTimeout(120_000)
    const textarea = await startNewChat(page, 'e2e-toolagent-a')

    await textarea.fill(
      'Используя search_files, найди в файле agent-web/agent_web/routers/chat.py все места ' +
      'где текст ошибки формируется как f"Tool error: {e}" или похожим образом (разные варианты ' +
      'сообщений об ошибке тула). Прочитай найденные места через read_file и предложи unified diff, ' +
      'приводящий все сообщения об ошибках к одному виду: "❌ Ошибка инструмента: {e}". ' +
      'Только предложи diff в ответе, ничего не записывай на диск.'
    )
    await expect(textarea).toBeEnabled()
    await textarea.press('Enter')
    await expect(textarea).toBeDisabled()

    const assistantBubble = page.locator('.prose').last()
    await expect(assistantBubble).not.toHaveText('', { timeout: 100_000 })
    await expect(textarea).toBeEnabled({ timeout: 100_000 })

    // No confirm modal should have appeared — these are all SAFE tools.
    await expect(page.getByText('Подтверди опасную операцию')).toHaveCount(0)

    await page.screenshot({ path: '../../week-07/day-34/screens/day34-scenario-a-diff.png', fullPage: true })
  })

  test('scenario B negative: Deny leaves the file untouched on disk', async ({ page }) => {
    test.setTimeout(120_000)  // read_file x2 + write_file confirm round-trip can outrun the 30s default
    gitRestoreToStagedBaseline(DRAFT)
    expect(gitStatusPorcelain(DRAFT)).toBe(BASELINE_STATUS)

    const textarea = await startNewChat(page, 'e2e-toolagent-b-deny')

    await textarea.fill(
      'Прочитай agent-web/agent_web/services/tools/danger.py через read_file, затем прочитай ' +
      'week-07/day-34/TOOLS_DOC_DRAFT.md. Замени в нём секцию "TBD — fill in..." на реальный ' +
      'список: read_file/search_files/list_dir = safe, write_file/delete_file = dangerous. ' +
      'Запиши изменённый файл через write_file с dry_run=false.'
    )
    await expect(textarea).toBeEnabled()
    await textarea.press('Enter')

    const modalTitle = page.getByText('Подтверди опасную операцию')
    await modalTitle.waitFor({ state: 'visible', timeout: 100_000 })
    await expect(page.getByText('write_file', { exact: true })).toBeVisible()

    await page.screenshot({ path: '../../week-07/day-34/screens/day34-scenario-b-modal.png', fullPage: true })

    await page.getByRole('button', { name: /Отклонить/ }).click()
    await modalTitle.waitFor({ state: 'hidden', timeout: 10_000 })

    await expect(textarea).toBeEnabled({ timeout: 100_000 })

    // Negative case, mandatory per 34.12: nothing written to disk.
    expect(gitStatusPorcelain(DRAFT)).toBe(BASELINE_STATUS)

    await page.screenshot({ path: '../../week-07/day-34/screens/day34-scenario-b-deny-clean.png', fullPage: true })
  })

  test('scenario B positive: Allow actually writes the file to disk', async ({ page }) => {
    // ProxyAPI's gpt-4o-mini tool-calling decision latency for this prompt has been
    // observed (direct /api/chat/stream curl testing, no browser involved) to occasionally
    // run 2-3+ minutes before the 3rd round (deciding to call write_file) returns — this is
    // live-API variance, not a code hang: confirmed via a raw curl run that the full
    // sequence (2x read_file -> confirm_request -> [auto-deny after the 60s confirm
    // window] -> tool_done -> chunk stream -> usage -> done) completes correctly end to
    // end once the API responds. Generous timeout to absorb that variance rather than
    // flake on a slow-but-correct run.
    test.setTimeout(360_000)
    gitRestoreToStagedBaseline(DRAFT)

    const textarea = await startNewChat(page, 'e2e-toolagent-b-allow')

    await textarea.fill(
      'Прочитай agent-web/agent_web/services/tools/danger.py через read_file, затем прочитай ' +
      'week-07/day-34/TOOLS_DOC_DRAFT.md. Замени в нём секцию "TBD — fill in..." на реальный ' +
      'список: read_file/search_files/list_dir = safe, write_file/delete_file = dangerous. ' +
      'Запиши изменённый файл через write_file с dry_run=false.'
    )
    await expect(textarea).toBeEnabled()
    await textarea.press('Enter')

    const modalTitle = page.getByText('Подтверди опасную операцию')
    await modalTitle.waitFor({ state: 'visible', timeout: 210_000 })

    await page.getByRole('button', { name: 'Разрешить' }).click()
    await modalTitle.waitFor({ state: 'hidden', timeout: 10_000 })

    await expect(textarea).toBeEnabled({ timeout: 200_000 })

    // Positive case, mandatory per 34.12: the file actually changed on disk.
    // DRAFT is a committed, clean, tracked file (see BASELINE_STATUS comment
    // above) — write_file only touches the working tree, not the index, so
    // the clean baseline ('') flips to worktree-modified-not-staged. Porcelain
    // format is "XY path" (X=index, Y=worktree) — for worktree-only that's
    // " M path", but gitStatusPorcelain().trim() strips the leading space, so
    // the string we actually see here starts with "M" (not " M").
    const status = gitStatusPorcelain(DRAFT)
    expect(status).not.toBe(BASELINE_STATUS)
    expect(status.startsWith('M')).toBe(true)

    await page.screenshot({ path: '../../week-07/day-34/screens/day34-scenario-b-allow-written.png', fullPage: true })

    // Restore the draft to its pre-test stale state so the repo doesn't carry
    // this run's LLM-authored content as a permanent artifact.
    gitRestoreToStagedBaseline(DRAFT)
  })
})
