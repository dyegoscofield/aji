---
name: frontend-design
description: |
  Cria interfaces frontend production-grade com alta qualidade de design. Use quando
  o usuário pedir para construir componentes web, páginas, landing pages, dashboards,
  ou qualquer UI. Gera código com escolhas estéticas distintivas, tipografia característica,
  paleta coesa e animações intencionais. Evita a estética genérica de IA (Inter, gradiente
  roxo no branco, cards básicos). SEMPRE use esta skill ao criar qualquer elemento visual
  para o AJI.
---

## Design Thinking

Antes de qualquer código, defina uma direção estética clara.

Para o AJI especificamente:
- Fundo: azul naval profundo #070F1E
- Acento: azul #2563EB + dourado #C8A96E
- Fontes: Bricolage Grotesque (display) + Instrument Serif (italic) + Geist Mono
- Estilo: dark mode sofisticado, autoridade + acessibilidade

## Princípios
- Tipografia distinta: nunca Inter, Roboto ou Arial como fonte principal
- Cor: variáveis CSS, modo escuro obrigatório
- Movimento: animações CSS de entrada com stagger (animation-delay)
- Layouts: assimétricos, sobreposição, grid-breaking
- Fundo: gradientes radiais suaves, grid de pontos, noise texture leve

## Para o AJI
Sempre aplicar:
```css
:root {
  --bg: #070F1E; --bg2: #0B1628;
  --blue: #2563EB; --gold: #C8A96E; --cyan: #38BDF8;
  --border: rgba(255,255,255,0.08);
  --muted: rgba(255,255,255,0.48);
}
```
