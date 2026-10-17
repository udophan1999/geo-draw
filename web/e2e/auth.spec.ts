import { expect, expectNoHorizontalOverflow, isPhone, test } from './fixtures'

test('mở app khi chưa đăng nhập thì chuyển sang /login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Đăng nhập' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('sai mật khẩu báo lỗi và xóa ô mật khẩu', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Tên đăng nhập').fill('khong-ton-tai')
  await page.getByLabel('Mật khẩu').fill('sai-mat-khau')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('alert')).toHaveText('Sai tên đăng nhập hoặc mật khẩu.')
  await expect(page.getByLabel('Mật khẩu')).toHaveValue('')
})

test('đăng ký kiểm tra mật khẩu trước khi gửi', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('Tên đăng nhập').fill('hocsinh')
  await page.getByLabel('Mật khẩu', { exact: true }).fill('123')
  await page.getByRole('button', { name: 'Đăng ký' }).click()
  await expect(page.getByRole('alert')).toHaveText('Mật khẩu phải có ít nhất 6 ký tự.')

  await page.getByLabel('Mật khẩu', { exact: true }).fill('matkhau123')
  await page.getByLabel('Nhập lại mật khẩu').fill('matkhau124')
  await page.getByRole('button', { name: 'Đăng ký' }).click()
  await expect(page.getByRole('alert')).toHaveText('Hai lần nhập mật khẩu không khớp.')
})

test('đăng ký, đăng xuất rồi đăng nhập lại', async ({ page }, testInfo) => {
  const name = `dk${testInfo.workerIndex}${Date.now().toString(36)}`
  await page.goto('/register')
  await page.getByLabel('Tên đăng nhập').fill(name)
  await page.getByLabel('Mật khẩu', { exact: true }).fill('matkhau123')
  await page.getByLabel('Nhập lại mật khẩu').fill('matkhau123')
  await page.getByRole('button', { name: 'Đăng ký' }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { name: /Chào bạn/ })).toBeVisible()

  // A taken name is refused with suggestions that fill the field when clicked.
  await page.context().clearCookies()
  await page.goto('/register')
  await page.getByLabel('Tên đăng nhập').fill(name)
  await page.getByLabel('Mật khẩu', { exact: true }).fill('matkhau123')
  await page.getByLabel('Nhập lại mật khẩu').fill('matkhau123')
  await page.getByRole('button', { name: 'Đăng ký' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  const suggestion = page.getByText('Gợi ý tên còn trống').locator('..').getByRole('button').first()
  const suggested = await suggestion.textContent()
  await suggestion.click()
  await expect(page.getByLabel('Tên đăng nhập')).toHaveValue(suggested!)
  await expect(page.getByRole('alert')).toBeHidden()

  await page.goto('/login')
  await page.getByLabel('Tên đăng nhập').fill(name)
  await page.getByLabel('Mật khẩu').fill('matkhau123')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('heading', { name: /Chào bạn/ })).toBeVisible()

  if (isPhone()) await page.getByRole('button', { name: 'Mở menu' }).click()
  await page.getByRole('button', { name }).click()
  await page.getByRole('menuitem', { name: 'Đăng xuất' }).click()
  await expect(page).toHaveURL(/\/login$/)
})

test('xóa tài khoản cần đúng mật khẩu', async ({ page, asUser }) => {
  const name = await asUser()
  if (isPhone()) await page.getByRole('button', { name: 'Mở menu' }).click()
  await page.getByRole('button', { name }).click()
  await page.getByRole('menuitem', { name: 'Cài đặt' }).click()
  await page.getByRole('button', { name: 'Xóa…' }).click()

  const dialog = page.getByRole('alertdialog')
  await dialog.getByLabel('Nhập mật khẩu để xác nhận').fill('sai-mat-khau')
  await dialog.getByRole('button', { name: 'Xóa vĩnh viễn' }).click()
  await expect(dialog.getByRole('alert')).toHaveText('Mật khẩu không đúng.')

  await dialog.getByLabel('Nhập mật khẩu để xác nhận').fill('matkhau123')
  await dialog.getByRole('button', { name: 'Xóa vĩnh viễn' }).click()
  await expect(page).toHaveURL(/\/login$/)

  // The account is gone: its name and password no longer sign in.
  await page.getByLabel('Tên đăng nhập').fill(name)
  await page.getByLabel('Mật khẩu').fill('matkhau123')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('alert')).toHaveText('Sai tên đăng nhập hoặc mật khẩu.')
})
