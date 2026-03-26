# Páginas, Rotas e Layouts

## Estrutura de Páginas

```
app/
├── (marketing)/             # Grupo público
│   ├── page.tsx             # Landing page
│   ├── planos/page.tsx
│   └── parceiros/page.tsx
├── (auth)/                  # Autenticação
│   ├── login/page.tsx
│   ├── cadastro/page.tsx
│   └── onboarding/page.tsx  # Wizard pós-cadastro
├── (dashboard)/             # Área logada
│   ├── layout.tsx           # Sidebar + header
│   ├── page.tsx             # Overview
│   ├── chat/
│   │   ├── page.tsx         # Lista de conversas
│   │   └── [id]/page.tsx    # Conversa individual
│   ├── documentos/page.tsx  # Upload de docs (plano Personalizado)
│   ├── relatorios/page.tsx
│   ├── equipe/page.tsx      # Gerenciar usuários do CNPJ
│   └── configuracoes/
│       ├── page.tsx
│       └── plano/page.tsx   # Upgrade/downgrade
└── (parceiro)/              # Portal do contador
    ├── layout.tsx
    ├── page.tsx             # Dashboard de indicações
    ├── indicacoes/page.tsx
    └── comissoes/page.tsx
```

## Onboarding (Wizard de Cadastro)

```tsx
// app/(auth)/onboarding/page.tsx
// Etapas:
// 1. Dados da empresa (CNPJ → preenchimento automático)
// 2. Escolha do plano
// 3. Configuração do acesso (usuários)
// 4. Primeiro chat (tutorial guiado)

const STEPS = [
  { id: 'company',  title: 'Sua empresa',     icon: 'Building' },
  { id: 'plan',     title: 'Escolha o plano',  icon: 'ClipboardList' },
  { id: 'team',     title: 'Sua equipe',       icon: 'Users' },
  { id: 'welcome',  title: 'Bem-vindo!',       icon: 'PartyPopper' },
]
```

## Portal do Parceiro Contador

```tsx
// app/(parceiro)/page.tsx — Dashboard de Indicações

export default function PartnerDashboard() {
  const { stats } = usePartnerStats()
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Indicações ativas"
          value={stats.activeReferrals}
          trend="+3 este mês"
          color="blue"
        />
        <StatCard
          label="Comissão do mês"
          value={`R$ ${stats.monthlyCommission.toFixed(2)}`}
          trend="R$ 59,40 / cliente"
          color="gold"
        />
        <StatCard
          label="Total acumulado"
          value={`R$ ${stats.totalEarned.toFixed(2)}`}
          color="green"
        />
      </div>

      <ReferralLinkCard code={stats.referralCode} />
      <ReferralsTable referrals={stats.referrals} />
    </div>
  )
}
```
