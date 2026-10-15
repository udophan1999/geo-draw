// Shared fixtures: every test fails on an uncaught exception or a console error, and gets
// helpers to enter the app as a guest or a fresh account.
import { test as base, expect, type Page } from '@playwright/test'

// Expected 4xx responses (wrong password, signed-out /me…) are logged by the browser itself.
const IGNORED_CONSOLE = [/Failed to load resource/]

type Fixtures = {
  /** Open the app as a guest ("Dùng thử không cần tài khoản"). */
  asGuest: () => Promise<void>
  /** Register a fresh account through the API (cookie lands in the page's context). */
  asUser: () => Promise<string>
}

export const test = base.extend<Fixtures & { consoleGuard: void }>({
  consoleGuard: [
    async ({ page }, use) => {
      const errors: string[] = []
      page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
      page.on('console', (message) => {
        if (message.type() !== 'error') return
        const text = message.text()
        if (!IGNORED_CONSOLE.some((pattern) => pattern.test(text))) errors.push(`console: ${text}`)
      })
      await use()
      expect(errors, 'Lỗi JavaScript trong trình duyệt').toEqual([])
    },
    { auto: true },
  ],

  asGuest: async ({ page }, use) => {
    await use(async () => {
      await page.goto('/login')
      await page.getByRole('button', { name: /Dùng thử không cần tài khoản/ }).click()
      await expect(page.getByRole('heading', { name: /Chào bạn/ })).toBeVisible()
    })
  },

  asUser: async ({ page }, use, testInfo) => {
    await use(async () => {
      const name = `hs${testInfo.workerIndex}${Date.now().toString(36)}`
      const response = await page.request.post('/api/auth/register', {
        data: { username: name, password: 'matkhau123' },
      })
      expect(response.ok()).toBeTruthy()
      await page.goto('/')
      await expect(page.getByRole('heading', { name: /Chào bạn/ })).toBeVisible()
      return name
    })
  },
})

export { expect }

/**
 * Nothing scrolls sideways except the boxes meant to (a display formula). The app shell is
 * `overflow-hidden`, so the document itself never grows: look at every scroll container.
 * ``scrollable`` adds selectors of boxes that are meant to scroll sideways.
 */
export async function expectNoHorizontalOverflow(page: Page, scrollable: string[] = []) {
  const offenders = await page.evaluate((extra) => {
    const allowed = ['.katex-display', ...extra].join(', ')
    const describe = (el: Element) =>
      `${el.tagName.toLowerCase()}.${[...el.classList].slice(0, 4).join('.')} (+${el.scrollWidth - el.clientWidth}px)`
    const found: string[] = []
    if (document.documentElement.scrollWidth > window.innerWidth) found.push(describe(document.documentElement))
    for (const el of document.querySelectorAll('body *')) {
      if (el.closest(allowed)) continue
      const { overflowX } = getComputedStyle(el)
      if ((overflowX === 'auto' || overflowX === 'scroll') && el.scrollWidth > el.clientWidth + 1) {
        found.push(describe(el))
      }
    }
    return found
  }, scrollable)
  expect(offenders, 'Có vùng bị tràn ngang').toEqual([])
}

/** Every visible element sits inside the viewport horizontally. */
export async function expectInViewport(page: Page, locator: ReturnType<Page['locator']>) {
  const box = await locator.boundingBox()
  const width = page.viewportSize()!.width
  expect(box, 'Phần tử không hiển thị').not.toBeNull()
  expect(box!.x).toBeGreaterThanOrEqual(0)
  expect(box!.x + box!.width).toBeLessThanOrEqual(width)
}

/** The message box (a Tiptap editor, not a textarea). */
export const composer = (page: Page) => page.getByRole('textbox', { name: 'Tin nhắn' })

/** Rendered formula chips in the message box. */
export const formulaChips = (page: Page) => composer(page).locator('[data-type="inline-math"]')

/** Type into the composer and send with Enter. */
export async function sendMessage(page: Page, text: string) {
  const box = composer(page)
  await box.fill(text)
  await box.press('Enter')
}

/** Phone projects (Pixel 7, iPhone): narrow screen, touch, menu behind "Mở menu". */
export const isPhone = () => Boolean(test.info().project.use.isMobile)
