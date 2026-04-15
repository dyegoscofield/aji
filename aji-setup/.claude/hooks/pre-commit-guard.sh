#!/bin/bash
# Hook: bloquear termos proibidos antes de qualquer commit
TERMOS="consultoria jurídica\|assessoria jurídica\|parecer jurídico\|substitui o advogado"
if git diff --cached --name-only | xargs grep -l "$TERMOS" 2>/dev/null; then
  echo "[AJI GUARD] BLOQUEADO: arquivo contém termos proibidos (OAB compliance)"
  echo "Substitua por: 'orientação jurídica preventiva'"
  exit 1
fi
exit 0
