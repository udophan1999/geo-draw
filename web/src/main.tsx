import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router'

import './index.css'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ApiError } from '@/lib/api'
import { useNewVersionNotice } from '@/lib/version'
import { AppLayout } from '@/routes/AppLayout'
import { LoginPage, RegisterPage } from '@/routes/auth'

// The chat page carries KaTeX, Markdown and the drawing tools: load it only inside the app,
// so /login stays light.
const ChatPage = lazy(() => import('@/routes/ChatPage').then((m) => ({ default: m.ChatPage })))
// The admin pages (and their charts) load only when an admin opens them.
const AdminLayout = lazy(() => import('@/routes/admin/AdminLayout').then((m) => ({ default: m.AdminLayout })))
const AdminOverview = lazy(() => import('@/routes/admin/AdminOverview').then((m) => ({ default: m.AdminOverview })))
const AdminUsers = lazy(() => import('@/routes/admin/AdminUsers').then((m) => ({ default: m.AdminUsers })))
const AdminUserDetail = lazy(() => import('@/routes/admin/AdminUserDetail').then((m) => ({ default: m.AdminUserDetail })))
const AdminPrompts = lazy(() => import('@/routes/admin/AdminPrompts').then((m) => ({ default: m.AdminPrompts })))
const adminRoutes = {
  path: '/admin',
  element: <Suspense fallback={null}><AdminLayout /></Suspense>,
  children: [
    { index: true, element: <Suspense fallback={null}><AdminOverview /></Suspense> },
    { path: 'users', element: <Suspense fallback={null}><AdminUsers /></Suspense> },
    { path: 'users/:userId', element: <Suspense fallback={null}><AdminUserDetail /></Suspense> },
    { path: 'prompts', element: <Suspense fallback={null}><AdminPrompts /></Suspense> },
  ],
}
const chatPage = (
  <Suspense fallback={null}>
    <ChatPage />
  </Suspense>
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
      // 4xx answers (not found, not allowed) will not change by retrying.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
})

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  adminRoutes,
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: chatPage },
      { path: '/c/:conversationId', element: chatPage },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

function VersionWatcher() {
  useNewVersionNotice()
  return null
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster position="top-center" richColors />
        <VersionWatcher />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
