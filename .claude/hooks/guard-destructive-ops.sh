#!/bin/bash
# Hook: guard-destructive-ops.sh
# Evento: PreToolUse (Bash)
# Propósito: Bloquear operações destrutivas e exigir confirmação
# Projeto: AJI — Assistente Jurídico Inteligente

COMMAND="$1"

# Padrões destrutivos bloqueados
DESTRUCTIVE_PATTERNS=(
    "rm -rf /"
    "rm -rf /*"
    "rm -rf ."
    "rm -rf .."
    "DROP DATABASE"
    "DROP TABLE"
    "DROP SCHEMA"
    "TRUNCATE TABLE"
    "DELETE FROM .* WHERE 1"
    "DELETE FROM .* WITHOUT"
    "git push --force"
    "git push -f"
    "git reset --hard"
    "git clean -fd"
    "chmod -R 777"
    ":(){ :|:& };:"
    "mkfs\."
    "dd if=/dev"
    "> /dev/sda"
    "alembic downgrade base"
)

# Padrões sensíveis que requerem atenção (dados do AJI)
SENSITIVE_PATTERNS=(
    "bank_data"
    "stripe_customer_id"
    "stripe_subscription_id"
    "jwt_secret"
    "OPENAI_API_KEY"
)

for pattern in "${DESTRUCTIVE_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qiE "$pattern"; then
        echo "BLOCKED: Operação destrutiva detectada: '$pattern'"
        echo "Comando: $COMMAND"
        echo "Se realmente necessário, execute manualmente com confirmação explícita."
        exit 2
    fi
done

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qiE "$pattern"; then
        echo "WARNING: Comando envolve dados sensíveis ($pattern)."
        echo "Verifique se não está expondo dados em logs ou output."
    fi
done

exit 0
