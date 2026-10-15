// Editing the student's last message: only the last one, in place, and MathMate answers again.
import { expect, formulaChips, isPhone, sendMessage, test } from './fixtures'

const REPLY = 'Em được phương trình nào?'
const NEW_REPLY = 'Mình đã xem đáp án mới của em.'

test.beforeEach(async ({ asGuest, page }) => {
  await asGuest()
  await sendMessage(page, 'Giải phương trình x + 3 = 5')
  await expect(page.getByText(REPLY)).toHaveCount(1)
})

const editButtons = (page: import('@playwright/test').Page) => page.getByRole('button', { name: 'Sửa tin nhắn' })

test('chỉ tin nhắn gần nhất có nút sửa', async ({ page }) => {
  await sendMessage(page, 'Em nghĩ x = 3')
  await expect(page.getByText(REPLY)).toHaveCount(2)
  await expect(editButtons(page)).toHaveCount(1)
  // The button sits next to the last bubble, not the problem.
  const row = page.getByRole('main').locator('div.group', { has: page.getByText('Em nghĩ x = 3') })
  await expect(row.getByRole('button', { name: 'Sửa tin nhắn' })).toHaveCount(1)
})

test('sửa tin nhắn cuối: MathMate trả lời lại, câu trả lời cũ được thay', async ({ page }) => {
  await sendMessage(page, 'Em nghĩ x = 3')
  await expect(page.getByText(REPLY)).toHaveCount(2)

  const row = page.getByRole('main').locator('div.group', { has: page.getByText('Em nghĩ x = 3') })
  if (!isPhone()) await row.hover()
  await row.getByRole('button', { name: 'Sửa tin nhắn' }).click()
  const box = page.getByRole('textbox', { name: 'Sửa tin nhắn' })
  await expect(box).toHaveText('Em nghĩ x = 3')
  await expect(box).toBeFocused()
  await box.fill('Em nghĩ x = 2, đáp án mới')
  await box.press('Enter')

  await expect(box).toHaveCount(0)
  await expect(page.getByText('Em nghĩ x = 2, đáp án mới')).toBeVisible()
  await expect(page.getByText('Em nghĩ x = 3')).toHaveCount(0)
  await expect(page.getByText(NEW_REPLY)).toBeVisible()
  await expect(page.getByText(REPLY)).toHaveCount(1) // the old reply to "x = 3" is gone
  // Still there after a reload: the server saved the edit.
  await page.reload()
  await expect(page.getByText(NEW_REPLY)).toBeVisible()
  await expect(page.getByText('Em nghĩ x = 3')).toHaveCount(0)
})

test('Esc hoặc Hủy thì không đổi gì', async ({ page }) => {
  await editButtons(page).click()
  const box = page.getByRole('textbox', { name: 'Sửa tin nhắn' })
  await box.fill('Đề khác hẳn')
  await box.press('Escape')
  await expect(box).toHaveCount(0)
  await expect(page.getByText('Giải phương trình x + 3 = 5').last()).toBeVisible()

  await editButtons(page).click()
  await page.getByRole('button', { name: 'Hủy' }).click()
  await expect(page.getByRole('textbox', { name: 'Sửa tin nhắn' })).toHaveCount(0)
  await expect(page.getByText(REPLY)).toHaveCount(1)
})

test('công thức trong tin nhắn hiện thành công thức khi sửa', async ({ page }) => {
  await sendMessage(page, 'Em tính được $x^2 = 4$')
  await expect(page.getByText(REPLY)).toHaveCount(2)
  await editButtons(page).click()
  const box = page.getByRole('textbox', { name: 'Sửa tin nhắn' })
  const chip = box.locator('[data-type="inline-math"]')
  await expect(chip).toHaveAttribute('data-latex', 'x^2 = 4')
  await expect(box).not.toContainText('$')
  await box.press('End')
  await box.pressSequentially(' nên đáp án mới')
  await box.press('Enter')
  await expect(page.getByText(NEW_REPLY)).toBeVisible()
  // The formula survived the round trip: rendered in the bubble, not as $source$.
  const bubble = page.getByRole('main').locator('div.group', { hasText: 'nên đáp án mới' })
  await expect(bubble.locator('.katex')).toBeVisible()
  await expect(formulaChips(page)).toHaveCount(0) // the message box itself stays empty
})

test('sửa đề bài (tin nhắn đầu tiên) khi chưa có tin nào khác', async ({ page }) => {
  await editButtons(page).click()
  const box = page.getByRole('textbox', { name: 'Sửa tin nhắn' })
  await box.fill('Giải phương trình 2x = 8, đáp án mới')
  await page.getByRole('group', { name: 'Đang sửa tin nhắn' }).getByRole('button', { name: 'Gửi' }).click()
  await expect(page.getByText(NEW_REPLY)).toBeVisible()
  await expect(page.getByText(REPLY)).toHaveCount(0)
})
