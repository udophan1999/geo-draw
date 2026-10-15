import { composer, expect, formulaChips, isPhone, test } from './fixtures'

test.beforeEach(async ({ asGuest }) => {
  await asGuest()
})

test('thanh ký hiệu chèn vào đúng vị trí con trỏ', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('x = 4')
  await expect(box).toHaveText('x = 4') // typed text is in the editor before the caret moves
  for (let i = 0; i < 4; i++) await box.press('ArrowLeft') // caret right after "x"
  // Under load the keys queue up faster than the caret moves: wait until it is there.
  await expect.poll(() => box.evaluate(() => getSelection()?.anchorOffset)).toBe(1)
  await page.getByRole('button', { name: 'Ký hiệu toán' }).click()
  await page.getByRole('toolbar', { name: 'Ký hiệu toán' }).getByRole('button', { name: 'Bình phương' }).click()
  await expect(box).toHaveText('x² = 4')
  await expect(box).toBeFocused()
})

test('gõ $…$ biến thành công thức hiển thị ngay trong ô nhập', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('Tính $\\frac{1}{2}$ nhé')
  const chip = formulaChips(page)
  await expect(chip).toHaveCount(1)
  await expect(chip).toHaveAttribute('data-latex', '\\frac{1}{2}')
  await expect(chip.locator('.mfrac')).toBeVisible()
  await expect(box).not.toContainText('$')
  await expect(box).toContainText('Tính')
  await expect(box).toContainText('nhé')
  // No separate preview box any more: the message box is the preview.
  await expect(page.getByLabel('Xem trước')).toHaveCount(0)
})

test('$ dùng như chữ thường thì không bị đổi thành công thức', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('Giá 5$ và 6$')
  await expect(formulaChips(page)).toHaveCount(0)
  await expect(box).toHaveText('Giá 5$ và 6$')
})

test('dán đề có $…$ thì công thức được hiển thị', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.evaluate((el) => {
    const data = new DataTransfer()
    data.setData('text/plain', 'Giải phương trình $x^2 - 5x + 6 = 0$ và $\\sqrt{x} = 2$')
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }))
  })
  await expect(formulaChips(page)).toHaveCount(2)
  await expect(formulaChips(page).first()).toHaveAttribute('data-latex', 'x^2 - 5x + 6 = 0')
  await expect(box).toContainText('Giải phương trình')
})

test('gửi tin có công thức: tin nhắn hiển thị công thức đã render', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('Rút gọn $\\frac{x}{2}$')
  await expect(formulaChips(page)).toHaveCount(1)
  await box.press('Enter')
  await expect(page).toHaveURL(/\/c\/[\w-]+$/)
  const bubble = page.getByRole('main').locator('.mfrac').first()
  await expect(bubble).toBeVisible()
  await expect(page.getByRole('main').getByText('$\\frac')).toHaveCount(0)
  await expect(box).toHaveText('')
})

test('Backspace xóa cả công thức như một ký tự', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('a $x^2$ b')
  await expect(formulaChips(page)).toHaveCount(1)
  for (let i = 0; i < 3; i++) await box.press('Backspace') // "b", the space, then the formula
  await expect(formulaChips(page)).toHaveCount(0)
  await expect(box).toHaveText('a')
})

test('Backspace ngay sau khi gõ $…$ trả lại mã LaTeX để sửa', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('a $x^2$')
  await expect(formulaChips(page)).toHaveCount(1)
  await box.press('Backspace')
  await expect(formulaChips(page)).toHaveCount(0)
  await expect(box).toHaveText('a $x^2$')
})

test('bấm vào công thức để sửa', async ({ page }) => {
  test.skip(isPhone(), 'gõ bàn phím thật; trên điện thoại dùng bàn phím ảo')
  const box = composer(page)
  await box.click()
  await box.pressSequentially('Tính $\\sqrt{2}$ nhé')
  await formulaChips(page).click()
  const dialog = page.getByRole('dialog', { name: 'Nhập công thức' })
  const update = dialog.getByRole('button', { name: 'Cập nhật công thức' })
  await expect(update).toBeEnabled()
  const field = dialog.locator('math-field')
  await expect.poll(() => field.evaluate((el) => (el as unknown as { value: string }).value)).toBe('\\sqrt{2}')
  await field.evaluate((el) => {
    (el as unknown as { value: string }).value = '\\sqrt{3}'
  })
  await update.click()
  await expect(dialog).toBeHidden()
  await expect(formulaChips(page)).toHaveCount(1)
  await expect(formulaChips(page)).toHaveAttribute('data-latex', '\\sqrt{3}')
  await expect(box).toContainText('Tính')
  await expect(box).toContainText('nhé')
})

test('Shift+Enter xuống dòng (một lần), không gửi', async ({ page }) => {
  const box = composer(page)
  await box.click()
  await box.pressSequentially('Dòng 1')
  await box.press('Shift+Enter')
  await box.pressSequentially('Dòng 2')
  await expect(box.locator('br:not(.ProseMirror-trailingBreak)')).toHaveCount(1)
  await expect(box).toContainText('Dòng 1')
  await expect(box).toContainText('Dòng 2')
  await expect(page).toHaveURL(/\/$/) // a sent message opens /c/<id>
})

test('gõ tiếng Việt bằng bộ gõ (IME): chữ đúng, Enter lúc đang soạn không gửi', async ({ page }) => {
  test.skip(test.info().project.name !== 'desktop', 'giả lập IME qua CDP của Chromium')
  const box = composer(page)
  await box.click()
  const cdp = await page.context().newCDPSession(page)
  // Telex: "tinhs" is composed as "tính" before it is committed.
  for (const text of ['t', 'ti', 'tin', 'tinh', 'tính']) {
    await cdp.send('Input.imeSetComposition', { text, selectionStart: text.length, selectionEnd: text.length })
  }
  await cdp.send('Input.insertText', { text: 'tính' })
  await box.pressSequentially(' $x^2$ ')
  await cdp.send('Input.imeSetComposition', { text: 'đi', selectionStart: 2, selectionEnd: 2 })
  await cdp.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 229 })
  await cdp.send('Input.insertText', { text: 'đi' })
  await expect(box).toHaveText(/^tính .+ đi$/)
  await expect(formulaChips(page)).toHaveCount(1)
  await expect(page).toHaveURL(/\/$/)
})

test('ô nhập tự giãn nhưng không quá 200px', async ({ page }) => {
  const box = composer(page)
  const before = (await box.boundingBox())!.height
  await box.click()
  for (let i = 0; i < 15; i++) {
    await box.pressSequentially(`Dòng ${i}`)
    await box.press('Shift+Enter')
  }
  const after = (await box.boundingBox())!.height
  expect(after).toBeGreaterThan(before)
  expect(after).toBeLessThanOrEqual(200)
})

test('đính kèm ảnh hiện ảnh xem trước và nút bỏ ảnh', async ({ page }) => {
  // 1×1 PNG
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64')
  await page.locator('input[type="file"]').setInputFiles({ name: 'de.png', mimeType: 'image/png', buffer: png })
  await expect(page.getByAltText('Ảnh đính kèm')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Gửi' })).toBeEnabled()
  await page.getByRole('button', { name: 'Bỏ ảnh' }).click()
  await expect(page.getByAltText('Ảnh đính kèm')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Gửi' })).toBeDisabled()
})
