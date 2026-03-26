# Chat Interface — Core UX do AJI

## Componente de Chat

```tsx
// app/(dashboard)/chat/[id]/page.tsx
'use client'

import { useChat } from '@/hooks/useChat'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ChatInput } from '@/components/chat/ChatInput'
import { TypingIndicator } from '@/components/chat/TypingIndicator'

export default function ChatPage({ params }: { params: { id: string } }) {
  const { messages, isTyping, sendMessage, conversation } = useChat(params.id)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full bg-[var(--bg-base)]">
      {/* Header da conversa */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-[var(--border)]">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--blue)] to-[var(--cyan)] 
                        flex items-center justify-center text-xs font-bold">
          AJ
        </div>
        <div>
          <p className="text-sm font-semibold text-white">AJI</p>
          <p className="text-xs text-[var(--text-muted)]">
            {conversation?.topic || 'Nova consulta'}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
          <span className="text-xs text-[var(--text-muted)]">Online</span>
        </div>
      </div>

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && <ChatEmptyState />}
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isTyping} />
    </div>
  )
}
```

## Hook de Chat com SSE Streaming

```tsx
// hooks/useChat.ts

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)

  const sendMessage = async (content: string) => {
    const userMsg = { id: uuid(), role: 'user', content, createdAt: new Date() }
    setMessages(prev => [...prev, userMsg])
    setIsTyping(true)

    const aiMsgId = uuid()
    setMessages(prev => [...prev, { id: aiMsgId, role: 'assistant', content: '', streaming: true }])

    try {
      const eventSource = new EventSource(
        `/api/chat/${conversationId}/stream?content=${encodeURIComponent(content)}`
      )

      eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'delta') {
          setMessages(prev => prev.map(m => 
            m.id === aiMsgId 
              ? { ...m, content: m.content + data.text }
              : m
          ))
        }
        if (data.type === 'done') {
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, streaming: false, sources: data.sources } : m
          ))
          setIsTyping(false)
          eventSource.close()
        }
      }
    } catch (err) {
      setIsTyping(false)
      toast.error('Erro ao enviar mensagem')
    }
  }

  return { messages, isTyping, sendMessage }
}
```
