// Whether this browser chose "Dùng thử không cần tài khoản". Without it (and without an
// account), the app opens on /login. Storage can be unavailable (private mode), so an
// in-memory copy keeps guest mode working until the page reloads.
const KEY = 'geo-draw:guest'
let memory = false

export function isGuestMode(): boolean {
  try {
    return memory || localStorage.getItem(KEY) === '1'
  } catch {
    return memory
  }
}

export function setGuestMode(on: boolean): void {
  memory = on
  try {
    if (on) localStorage.setItem(KEY, '1')
    else localStorage.removeItem(KEY)
  } catch {
    // storage blocked: the in-memory flag is enough for this page load
  }
}
