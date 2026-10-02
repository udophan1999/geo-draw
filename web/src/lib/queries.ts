import { useQuery, type QueryClient } from '@tanstack/react-query'

import { api, type ConversationDetail, type Message } from '@/lib/api'

export const keys = {
  me: ['me'] as const,
  settings: ['settings'] as const,
  examples: ['examples'] as const,
  help: ['help'] as const,
  conversations: ['conversations'] as const,
  conversation: (id: string) => ['conversation', id] as const,
  editor: (messageId: string) => ['editor', messageId] as const,
  scene: (messageId: string) => ['scene', messageId] as const,
  log: (messageId: string) => ['log', messageId] as const,
  adminUsers: (q: string) => ['admin', 'users', q] as const,
  adminPrompts: ['admin', 'prompts'] as const,
  adminStats: (days: number) => ['admin', 'stats', days] as const,
}

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.me })
export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: api.settings })
export const useExamples = () =>
  useQuery({ queryKey: keys.examples, queryFn: api.examples, staleTime: Infinity })
export const useHelp = () => useQuery({ queryKey: keys.help, queryFn: api.help, staleTime: Infinity })
export const useConversations = () =>
  useQuery({ queryKey: keys.conversations, queryFn: api.conversations })
export const useConversation = (id: string | undefined) =>
  useQuery({
    queryKey: keys.conversation(id ?? ''),
    queryFn: () => api.conversation(id!),
    enabled: Boolean(id),
  })

/** Insert or replace a message in a cached conversation (from SSE or a re-render). */
export function upsertMessage(client: QueryClient, message: Message) {
  client.setQueryData<ConversationDetail>(keys.conversation(message.conversation_id), (old) => {
    if (!old) return old
    const index = old.messages.findIndex((m) => m.id === message.id)
    const messages = [...old.messages]
    if (index >= 0) messages[index] = message
    else messages.push(message)
    return { ...old, messages }
  })
}
