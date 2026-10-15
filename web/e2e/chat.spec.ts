import { composer, expect, expectInViewport, expectNoHorizontalOverflow, isPhone, sendMessage, test } from './fixtures'

test.beforeEach(async ({ asGuest }) => {
  await asGuest()
})

test('trang chào hiện đề mẫu và không tràn ngang', async ({ page }) => {
  await expect(page.getByText('Thử một đề mẫu')).toBeVisible()
  await expect(page.locator('button', { hasText: /\S/ }).filter({ has: page.locator('[data-slot="badge"]') }).first())
    .toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectInViewport(page, page.getByRole('button', { name: 'Gửi' }))
})

test('gửi đề: hiện tin nhắn, trợ giảng trả lời, lên bậc gợi ý', async ({ page }) => {
  await sendMessage(page, 'Giải phương trình x + 3 = 5')
  await expect(page).toHaveURL(/\/c\/[\w-]+$/)
  await expect(page.getByRole('main').getByText('Giải phương trình x + 3 = 5')).toBeVisible()
  await expect(page.getByText('Em được phương trình nào?')).toBeVisible()
  // The progress tag is stripped, both while streaming and once saved.
  await expect(page.getByText('[[bac')).toHaveCount(0)
  await expect(page.getByText('▍')).toHaveCount(0)
  await expect(page.getByLabel(/Bậc 2\/5: Nhớ kiến thức/)).toBeVisible()
  await expect(composer(page)).toHaveText('')
  await expect(composer(page).locator('p').first()).toHaveAttribute('data-placeholder', /Trả lời câu hỏi/)
  // Not geometry: no figure panel, "Vẽ hình" is offered instead.
  await expect(page.getByRole('button', { name: 'Vẽ hình' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('tiêu đề do AI đặt hiện trong danh sách', async ({ page }) => {
  await sendMessage(page, 'Tính 12 x 15')
  await expect(page.getByText('Em được phương trình nào?')).toBeVisible()
  if (isPhone()) await page.getByRole('button', { name: 'Mở menu' }).click()
  await expect(page.getByRole('link', { name: 'Bài thử nghiệm' })).toBeVisible()
})

test('lỗi AI hiện thành tin nhắn lỗi, không làm hỏng trang', async ({ page }) => {
  await sendMessage(page, 'Thử lỗi AI: tính 1 + 1')
  await expect(page.getByText(/Máy chủ AI trả về lỗi HTTP 500/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Gửi' })).toBeDisabled() // empty box
  await composer(page).fill('em thử lại')
  await expect(page.getByRole('button', { name: 'Gửi' })).toBeEnabled()
})

test('công thức rất dài không đẩy nút Gửi ra khỏi màn hình', async ({ page }) => {
  await sendMessage(page, 'Cho em xem công thức dài')
  await expect(page.locator('.katex-display').first()).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectInViewport(page, page.getByRole('button', { name: 'Gửi' }))
})

test('chuyển sang lời giải cần xác nhận', async ({ page }) => {
  await sendMessage(page, 'Giải phương trình 2x = 8')
  await expect(page.getByText('Em được phương trình nào?')).toBeVisible()
  await page.getByRole('button', { name: 'Lời giải chi tiết' }).click()
  const dialog = page.getByRole('alertdialog')
  await expect(dialog.getByText('Xem lời giải chi tiết?')).toBeVisible()
  await dialog.getByRole('button', { name: 'Tiếp tục tự làm' }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByText('Đang xem lời giải đầy đủ')).toHaveCount(0)

  await page.getByRole('button', { name: 'Lời giải chi tiết' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Xem lời giải' }).click()
  await expect(page.getByText('Đang xem lời giải đầy đủ')).toBeVisible()
})
