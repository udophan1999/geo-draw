import { expect, isPhone, sendMessage, test } from './fixtures'

test('đổi tên và xóa cuộc trò chuyện', async ({ page, asUser }) => {
  const mobile = isPhone()
  await asUser()
  await sendMessage(page, 'Giải phương trình x - 1 = 0')
  await expect(page.getByText('Em được phương trình nào?')).toBeVisible()
  if (mobile) await page.getByRole('button', { name: 'Mở menu' }).click()

  const item = page.getByRole('listitem').filter({ has: page.getByRole('link', { name: 'Bài thử nghiệm' }) })
  await item.hover()
  await item.getByRole('button', { name: 'Tùy chọn cuộc trò chuyện' }).click()
  await page.getByRole('menuitem', { name: 'Đổi tên' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('textbox')).toHaveValue('Bài thử nghiệm')
  await dialog.getByRole('textbox').fill('Phương trình bậc nhất')
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(dialog).toBeHidden()
  const renamed = page.getByRole('link', { name: 'Phương trình bậc nhất' })
  await expect(renamed).toBeVisible()

  const row = page.getByRole('listitem').filter({ has: renamed })
  await row.hover()
  await row.getByRole('button', { name: 'Tùy chọn cuộc trò chuyện' }).click()
  await page.getByRole('menuitem', { name: 'Xóa' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Xóa' }).click()
  await expect(page).toHaveURL(/\/$/)
  // On a phone the menu stays open after a delete: the empty list shows right there.
  await expect(page.getByText('Chưa có cuộc trò chuyện nào.')).toBeVisible()
})

test('mở cuộc trò chuyện không tồn tại thì quay về trang đầu', async ({ page, asUser }) => {
  await asUser()
  await page.goto('/c/khong-co')
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { name: /Chào bạn/ })).toBeVisible()
})

test('menu trên điện thoại mở và đóng được', async ({ page, asGuest }) => {
  test.skip(!isPhone(), 'chỉ có trên màn hình hẹp')
  await asGuest()
  const newChat = page.getByRole('button', { name: 'Cuộc trò chuyện mới' })
  await expect(newChat).not.toBeInViewport()
  await page.getByRole('button', { name: 'Mở menu' }).click()
  await expect(newChat).toBeInViewport()
  // The backdrop covers the whole screen under the menu: tap its visible part, on the right.
  const backdrop = page.getByRole('button', { name: 'Đóng menu' })
  const { width } = (await backdrop.boundingBox())!
  await backdrop.click({ position: { x: width - 20, y: 200 } })
  await expect(newChat).not.toBeInViewport()
})
