// The ∑ "Nhập công thức" dialog: MathLive (loaded on demand) plus a Word-like template gallery.
import type { Locator, Page } from '@playwright/test'

import { composer, expect, expectNoHorizontalOverflow, formulaChips, isPhone, test } from './fixtures'

test.beforeEach(async ({ asGuest }) => {
  await asGuest()
})

/** The editing logic is the same on every screen; phones get their own tests at the end. */
const desktopOnly = () =>
  test.skip(isPhone(), 'logic chung, kiểm tra trên desktop')

/** Open the dialog and wait until MathLive is loaded and focused. */
async function openFormula(page: Page) {
  await page.getByRole('button', { name: 'Nhập công thức' }).click()
  const dialog = page.getByRole('dialog', { name: 'Nhập công thức' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Chèn vào tin nhắn' })).toBeEnabled()
  const field = dialog.locator('math-field')
  await expect(field).toBeFocused()
  return { dialog, field }
}

test('mở hộp công thức: MathLive tải xong, có thư viện mẫu', async ({ page }) => {
  desktopOnly()
  const { dialog } = await openFormula(page)
  await expect(dialog.getByRole('tab', { name: 'Cơ bản' })).toHaveAttribute('aria-selected', 'true')
  const fraction = dialog.getByRole('button', { name: 'Phân số', exact: true })
  await expect(fraction).toBeEnabled()
  await expect(fraction.locator('.katex')).toBeVisible() // tiles are drawn by KaTeX
})

test('công thức đơn giản được chèn dạng Unicode, cách chữ xung quanh', async ({ page }) => {
  desktopOnly()
  const box = composer(page)
  await box.fill('Tính')
  const { dialog } = await openFormula(page)
  await page.keyboard.type('x^2')
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  await expect(dialog).toBeHidden()
  await expect(box).toHaveText(/^Tính x²\s$/)
  await expect(box).toBeFocused()
  await expect(formulaChips(page)).toHaveCount(0) // plain Unicode text, no formula chip
})

test('mẫu phân số: điền ô trống bằng Tab, giữ LaTeX và có xem trước', async ({ page }) => {
  desktopOnly()
  const { dialog } = await openFormula(page)
  await dialog.getByRole('button', { name: 'Phân số', exact: true }).click()
  await page.keyboard.type('1')
  await page.keyboard.press('Tab')
  await page.keyboard.type('2')
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  // Shown rendered in the message box itself, as a formula chip (Notion-style).
  const chip = formulaChips(page)
  await expect(chip).toHaveCount(1)
  await expect(chip).toHaveAttribute('data-latex', /^\\frac\{?1\}?\{?2\}?$/)
  await expect(chip.locator('.mfrac')).toBeVisible()
  await expect(composer(page)).not.toContainText('$')
})

test('bộ gõ tiếng Việt (IME) điền vào ô trống của mẫu, không xóa phân số', async ({ page }) => {
  desktopOnly()
  const { dialog, field } = await openFormula(page)
  await dialog.getByRole('button', { name: 'Phân số', exact: true }).click()
  // Windows' Vietnamese Telex keyboard composes "a" → "ă" before committing it.
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Input.imeSetComposition', { text: 'a', selectionStart: 1, selectionEnd: 1 })
  await cdp.send('Input.imeSetComposition', { text: 'ă', selectionStart: 1, selectionEnd: 1 })
  await cdp.send('Input.insertText', { text: 'ă' })
  await page.keyboard.press('Tab')
  await page.keyboard.type('2')
  expect(await field.evaluate((el) => (el as unknown as { value: string }).value)).toBe('\\frac{ă}{2}')
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  await expect(formulaChips(page).locator('.mfrac')).toHaveCount(1)
})

test('Enter trong ô công thức chèn luôn', async ({ page }) => {
  desktopOnly()
  const { dialog } = await openFormula(page)
  await page.keyboard.type('a+b')
  await page.keyboard.press('Enter')
  await expect(dialog).toBeHidden()
  await expect(composer(page)).toHaveText(/^a\+b\s$/)
})

test('Hủy, Esc hoặc chèn công thức rỗng không đổi tin nhắn', async ({ page }) => {
  desktopOnly()
  const box = composer(page)
  await box.fill('Đề bài')

  let { dialog } = await openFormula(page)
  await page.keyboard.type('y^3')
  await dialog.getByRole('button', { name: 'Hủy' }).click()
  await expect(dialog).toBeHidden()

  ;({ dialog } = await openFormula(page))
  await page.keyboard.press('Escape') // MathLive may close its own menu first
  if (await dialog.isVisible()) await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  ;({ dialog } = await openFormula(page))
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  await expect(dialog).toBeHidden()
  await expect(box).toHaveText('Đề bài')
})

test('mở lại hộp thì ô công thức trống', async ({ page }) => {
  desktopOnly()
  let { dialog, field } = await openFormula(page)
  await page.keyboard.type('z')
  await dialog.getByRole('button', { name: 'Hủy' }).click()
  ;({ dialog, field } = await openFormula(page))
  expect(await field.evaluate((el) => (el as unknown as { value: string }).value)).toBe('')
})

test('chuyển tab thư viện mẫu và chèn ký hiệu hình học', async ({ page }) => {
  desktopOnly()
  const { dialog } = await openFormula(page)
  await dialog.getByRole('tab', { name: 'Hình học' }).click()
  await expect(dialog.getByRole('button', { name: 'Phân số', exact: true })).toBeHidden()
  await dialog.getByRole('button', { name: 'Tam giác', exact: true }).click()
  await page.keyboard.type('ABC')
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  await expect(composer(page)).toHaveText(/^△ABC\s$/)
})

test('hộp công thức vừa màn hình, chỉ danh sách tab được cuộn ngang', async ({ page }) => {
  const { dialog } = await openFormula(page)
  await expectNoHorizontalOverflow(page, ['[role="tablist"]'])
  const box = (await dialog.boundingBox())!
  const width = page.viewportSize()!.width
  expect(box.x).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width).toBeLessThanOrEqual(width)
  // Every tab can be reached, even when the list scrolls on a phone.
  const last = dialog.getByRole('tab').last()
  await last.click()
  await expect(last).toHaveAttribute('aria-selected', 'true')
  await expect(dialog.getByRole('button', { name: 'Chèn vào tin nhắn' })).toBeInViewport()
})

test('bàn phím toán mở sẵn, không che nút Chèn và bấm được', async ({ page }) => {
  const { dialog, field } = await openFormula(page)
  const keyboard = page.locator('.ML__keyboard')
  await expect(keyboard).toBeVisible() // open on every screen, so students know it is there
  // It slides up: wait until it stops moving before looking at what it covers.
  const keys = keyboard.locator('.MLK__keycap').filter({ visible: true }).first()
  await expect.poll(async () => {
    const before = JSON.stringify(await keys.boundingBox())
    await page.waitForTimeout(150)
    return before === JSON.stringify(await keys.boundingBox())
  }).toBe(true)

  // The insert button is what the finger lands on, not a key of the keyboard.
  const insert = dialog.getByRole('button', { name: 'Chèn vào tin nhắn' })
  const box = (await insert.boundingBox())!
  const onButton = await page.evaluate(([x, y]) => {
    const hit = document.elementFromPoint(x, y)
    return Boolean(hit?.closest('[data-slot="dialog-footer"]'))
  }, [box.x + box.width / 2, box.y + box.height / 2])
  expect(onButton, 'Bàn phím ảo che nút "Chèn vào tin nhắn"').toBe(true)

  // Its keys type into the formula (a keycap's text also holds its shifted variant: "7■7").
  await keyboard.locator('.MLK__keycap', { hasText: /^7/ }).filter({ visible: true }).first().click({ timeout: 3000 })
  expect(await field.evaluate((el) => (el as unknown as { value: string }).value)).toBe('7')
  await expect(dialog).toBeVisible() // a tap on the keyboard is not a tap outside the dialog

  await insert.click()
  await expect(dialog).toBeHidden()
  await expect(composer(page)).toHaveText(/^7\s$/)
  await expect(keyboard).toBeHidden() // closing the dialog puts the keyboard away
})

test('điện thoại: chạm mẫu phân số rồi chạm phím ảo để điền, hộp không bị đóng', async ({ page }) => {
  test.skip(!isPhone(), 'bàn phím ảo chỉ bật trên màn hình cảm ứng')
  const { dialog, field } = await openFormula(page)
  const keyboard = page.locator('.ML__keyboard')
  await expect(keyboard).toBeVisible()
  const key = (text: RegExp) => keyboard.locator('.MLK__keycap', { hasText: text }).filter({ visible: true }).first()
  const value = () => field.evaluate((el) => (el as unknown as { value: string }).value)

  await dialog.getByRole('button', { name: 'Phân số', exact: true }).tap()
  await key(/^1/).tap()
  await expect(dialog).toBeVisible()
  await expect.poll(value).toBe('\\frac{1}{\\placeholder{}}')
  await page.keyboard.press('Tab')
  await key(/^2/).tap()
  await expect.poll(value).toMatch(/^\\frac\{?1\}?\{?2\}?$/) // MathLive may write \frac12

  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).tap()
  await expect(dialog).toBeHidden()
  await expect(formulaChips(page).locator('.mfrac')).toHaveCount(1)
})

test('bàn phím toán vẫn mở khi đổi tab và bấm mẫu', async ({ page }) => {
  const { dialog } = await openFormula(page)
  const keyboard = page.locator('.ML__keyboard')
  // A finger on phones: a mouse click would open the gallery's tooltips, which on a narrow
  // screen sit over the keyboard button (and a finger never opens them).
  const press = (target: Locator) => (isPhone() ? target.tap() : target.click())
  await expect(keyboard).toBeVisible()
  await press(dialog.getByRole('tab', { name: 'Hình học' }))
  await press(dialog.getByRole('button', { name: 'Tam giác', exact: true }))
  await expect(keyboard).toBeVisible()
  // Its button in the field closes it, for good (it used to come back on touch screens).
  await press(dialog.locator('math-field').locator('[part=virtual-keyboard-toggle]'))
  await expect(keyboard).toBeHidden()
})

test('menu của ô công thức bằng tiếng Việt', async ({ page }) => {
  desktopOnly()
  const { dialog } = await openFormula(page)
  await dialog.locator('math-field').locator('[part=menu-toggle]').click()
  await expect(page.getByText('Chèn ma trận')).toBeVisible()
  await expect(page.getByText('Chọn tất cả')).toBeVisible()
  await expect(page.getByText('Insert Matrix')).toHaveCount(0)
  await expect(page.getByText('Select All')).toHaveCount(0)
})

test('nút căn trên thanh ký hiệu mở hộp công thức với căn có sẵn ô trống', async ({ page }) => {
  desktopOnly()
  const box = composer(page)
  await box.fill('Tính')
  await page.getByRole('button', { name: 'Ký hiệu toán' }).click()
  const symbols = page.getByRole('toolbar', { name: 'Ký hiệu toán' })
  await symbols.getByRole('button', { name: 'Căn bậc hai' }).click()
  const dialog = page.getByRole('dialog', { name: 'Nhập công thức' })
  await expect(dialog.locator('math-field')).toBeFocused()
  await page.keyboard.type('2') // into the root's slot
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  // A root stays a formula, drawn with its bar (as text, √123 would not show where it ends).
  await expect(formulaChips(page)).toHaveCount(1)
  await expect(formulaChips(page)).toHaveAttribute('data-latex', /^\\sqrt\{?2\}?$/) // MathLive may write \sqrt2

  await symbols.getByRole('button', { name: 'Căn bậc ba' }).click()
  await expect(dialog.locator('math-field')).toBeFocused()
  await page.keyboard.type('8')
  await dialog.getByRole('button', { name: 'Chèn vào tin nhắn' }).click()
  await expect(formulaChips(page)).toHaveCount(2)
  await expect(formulaChips(page).last()).toHaveAttribute('data-latex', '\\sqrt[3]{8}')
})
