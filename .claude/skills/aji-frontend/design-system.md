# Design System e Paleta de Cores

## Stack & Convenções

```
Framework:    Next.js 14 (App Router)
Styling:      Tailwind CSS + CSS Variables para tema
Estado:       Zustand (global) + React Query (server state)
Formulários:  React Hook Form + Zod
Chat RT:      Server-Sent Events (SSE) para streaming
HTTP:         Axios com interceptors de auth
Icons:        Lucide React
Fontes:       Bricolage Grotesque (display) + Inter (corpo)
Animações:    Framer Motion (transições) + CSS keyframes (micro)
```

## Paleta de Cores (CSS Variables)

```css
:root {
  /* Backgrounds */
  --bg-base:    #070F1E;
  --bg-surface: #0B1628;
  --bg-raised:  #0F1E38;
  --bg-overlay: #132040;
  
  /* Brand */
  --blue:       #2563EB;
  --blue-hi:    #3B7DFF;
  --blue-dim:   rgba(37, 99, 235, 0.15);
  --gold:       #C8A96E;
  --cyan:       #38BDF8;
  
  /* Text */
  --text-primary:   #FFFFFF;
  --text-secondary: rgba(255,255,255,0.6);
  --text-muted:     rgba(255,255,255,0.35);
  
  /* Borders */
  --border:     rgba(255,255,255,0.08);
  --border-hi:  rgba(37,99,235,0.45);
  
  /* Status */
  --success:    #10B981;
  --warning:    #F59E0B;
  --error:      #EF4444;
}
```

## Componentes Base Reutilizáveis

```tsx
// Botão primário
<Button variant="primary" size="md" loading={isLoading}>Confirmar</Button>

// Card com borda gradiente
<Card variant="elevated" glow>...</Card>

// Badge de status
<Badge status="active">Ativo</Badge>
<Badge status="trial">Trial — 5 dias restantes</Badge>
<Badge status="suspended">Suspenso</Badge>

// Toast notifications
toast.success('Consulta enviada')
toast.error('Erro ao processar')
toast.info('Sua trial expira em 3 dias', { action: { label: 'Ver planos', href: '/planos' }})
```

## Regras de UX

1. **Mobile first:** Todo componente deve funcionar em 375px
2. **Loading states:** Sempre mostrar skeleton ou spinner durante fetch
3. **Empty states:** Sempre ter estado vazio com CTA claro
4. **Error handling:** Sempre ter fallback visual para erros de API
5. **Acessibilidade:** `aria-label` em todos os ícones, contraste WCAG AA
6. **Performance:** Lazy load componentes pesados, imagens com `next/image`
7. **Feedback imediato:** Atualização otimista antes da resposta do servidor
