// Copying a sent message: text with $latex$ formulas, pasted back as formulas.
import type { Page } from '@playwright/test'

import { composer, expect, formulaChips, isPhone, sendMessage, test } from './fixtures'

const REPLY = 'Em được phương trình nào?'
const WITH_FORMULA = 'Em tính được $x^2 = 4$ nên x = 2'

/** Two messages: an older one with a formula, then the latest. */
async function twoMessages(page: Page) {
  await sendMessage(page, WITH_FORMULA)
  await expect(page.getByText(REPLY)).toHaveCount(1)
  await sendMessage(page, 'Em làm tiếp nhé')
  await expect(page.getByText(REPLY)).toHaveCount(2)
}

const bubble = (page: Page, text: string) => page.getByRole('main').locator('div.group', { hasText: text })

test.beforeEach(async ({ asGuest }) => {
  await asGuest()
})

test('tin cũ có nút sao chép (không có nút sửa), chép cả công thức dạng $…$', async ({ page }) => {
  // Record what is copied, the same way in every browser.
  await page.addInitScript(() => {
    const copied: string[] = []
    Object.assign(window, { __copied: copied })
    navigator.clipboard.writeText = async (text: string) => {
      copied.push(text)
    }
  })
  await page.reload()
  await twoMessages(page)
  const older = bubble(page, 'nên x = 2')
  await expect(older.getByRole('button', { name: 'Sửa tin nhắn' })).toHaveCount(0)
  if (!isPhone()) await older.hover()
  await older.getByRole('button', { name: 'Sao chép tin nhắn' }).click()
  await expect(older.getByRole('button', { name: 'Đã sao chép' })).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __copied: string[] }).__copied)).toEqual([WITH_FORMULA])
  await expect(older.getByRole('button', { name: 'Sao chép tin nhắn' })).toBeVisible({ timeout: 3000 })
})

test('chép rồi dán vào ô nhập: công thức hiện lại thành công thức', async ({ page, context }) => {
  test.skip(test.info().project.name !== 'desktop', 'clipboard thật chỉ cấp quyền được trên Chromium')
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await twoMessages(page)
  const older = bubble(page, 'nên x = 2')
  await older.hover()
  await older.getByRole('button', { name: 'Sao chép tin nhắn' }).click()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(WITH_FORMULA)

  await composer(page).click()
  await page.keyboard.press('ControlOrMeta+V')
  await expect(formulaChips(page)).toHaveCount(1)
  await expect(formulaChips(page)).toHaveAttribute('data-latex', 'x^2 = 4')
  await expect(composer(page)).toContainText('Em tính được')
})

test('không có Clipboard API vẫn chép được', async ({ page }) => {
  test.skip(test.info().project.name !== 'desktop', 'cách chép dự phòng, kiểm tra trên Chromium')
  await page.addInitScript(() => {
    const copied: string[] = []
    Object.assign(window, { __copied: copied })
    navigator.clipboard.writeText = () => Promise.reject(new Error('not allowed'))
    document.addEventListener('copy', () => {
      const area = document.activeElement
      if (area instanceof HTMLTextAreaElement) copied.push(area.value)
    })
  })
  await page.reload()
  await twoMessages(page)
  const older = bubble(page, 'nên x = 2')
  await older.hover()
  await older.getByRole('button', { name: 'Sao chép tin nhắn' }).click()
  await expect(older.getByRole('button', { name: 'Đã sao chép' })).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __copied: string[] }).__copied)).toEqual([WITH_FORMULA])
})
