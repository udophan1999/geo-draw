// /admin/users: every account and the actions on it.
import { UsersPanel } from '@/components/admin/UsersPanel'
import { useMe } from '@/lib/queries'
import { PageHeader } from '@/routes/admin/AdminLayout'

export function AdminUsers() {
  const me = useMe()  // already loaded by the layout's guard
  return (
    <>
      <PageHeader title="Người dùng"
                  description="Đặt lại mật khẩu, đổi hạn mức AI, phân quyền, khóa hoặc xóa tài khoản." />
      <UsersPanel meId={me.data?.user?.id ?? ''} />
    </>
  )
}
