// /admin/prompts: the tutor's system prompts.
import { PromptsPanel } from '@/components/admin/PromptsPanel'
import { PageHeader } from '@/routes/admin/AdminLayout'

export function AdminPrompts() {
  return (
    <>
      <PageHeader title="System prompt" description="Cách trợ giảng gợi ý và trình bày lời giải." />
      <PromptsPanel />
    </>
  )
}
