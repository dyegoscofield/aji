#!/bin/bash
# Hook: quality-gate.sh
# Evento: Stop (antes de finalizar a sessão)
# Propósito: Verificar qualidade mínima antes de encerrar
# Projeto: AJI — Assistente Jurídico Inteligente

echo "QUALITY GATE — Verificação antes de encerrar:"
echo ""
echo "Checklist obrigatório:"
echo "  [ ] Todas as queries ao banco incluem tenant_id?"
echo "  [ ] Dados sensíveis (CNPJ, bank_data) não estão expostos em logs?"
echo "  [ ] Respostas ao empresário incluem disclaimer jurídico?"
echo "  [ ] Código novo tem type hints (Python) ou TypeScript types?"
echo "  [ ] Mudanças foram explicadas com justificativa técnica?"
echo "  [ ] Se discordou de algo, registrou a opinião com embasamento?"
echo "  [ ] Testes foram criados ou atualizados para as mudanças?"
echo ""
echo "Se algum item não foi atendido, informe o usuário antes de encerrar."

exit 0
