#!/bin/bash
# Hook: transparency-check.sh
# Evento: PostToolUse (Edit/Write)
# Propósito: Após editar/criar código, lembrar o agente de explicar as mudanças
# Projeto: AJI — Assistente Jurídico Inteligente

FILE_INFO="$1"

echo "TRANSPARENCY: Arquivo modificado/criado."
echo "Lembre-se de explicar ao usuário:"
echo "  1. O QUE foi alterado (resumo das mudanças)"
echo "  2. POR QUE foi alterado (justificativa técnica)"
echo "  3. IMPACTO em outros módulos (se houver)"
echo ""
echo "Se a mudança envolve lógica de multi-tenancy, confirme que tenant_id está presente em todas as queries."
echo "Se a mudança envolve resposta ao empresário, confirme que o disclaimer jurídico está incluído."

exit 0
