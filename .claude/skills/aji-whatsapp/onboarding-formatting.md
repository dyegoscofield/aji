# Onboarding e Formatação de Mensagens WhatsApp

## Mensagens de Onboarding

```python
ONBOARDING_MESSAGES = {
    'boas_vindas': """
*Olá! Bem-vindo ao AJI — Assistente Jurídico Inteligente.*

Sou um assistente especializado em orientação jurídica para empresas brasileiras. Posso ajudar com dúvidas sobre:

• Direito do Trabalho
• Contratos empresariais  
• Cobrança de inadimplentes
• Prevenção de riscos jurídicos

Para começar, qual é o CNPJ da sua empresa?
""",

    'cnpj_invalido': "CNPJ não encontrado na Receita Federal. Verifique e tente novamente.",
    
    'cnpj_confirmacao': """
*Empresa encontrada:*
{razao_social}
CNPJ: {cnpj}

Está correto? Responda *SIM* para confirmar ou *NÃO* para tentar novamente.
""",

    'cadastro_completo': """
*Conta criada com sucesso!*

Você tem *7 dias gratuitos* para experimentar o AJI.

Pode fazer sua primeira pergunta agora! Por exemplo:
_"Posso demitir um funcionário que faltou 3 dias sem aviso?"_
""",

    'ja_cadastrado': """
*Você já tem uma conta AJI.*

Pode fazer sua pergunta jurídica agora!
""",
}
```

## Formatação de Mensagens para WhatsApp

```python
def format_for_whatsapp(text: str) -> str:
    """
    WhatsApp usa formatação própria:
    *bold* = negrito
    _italic_ = itálico
    ~strikethrough~ = riscado
    ```code``` = monoespaçado
    """
    # **bold** → *bold*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # ### heading → *HEADING*
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # Bullet list com bullet
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)
    # Limitar tamanho (WhatsApp: 4096 chars por mensagem)
    if len(text) > 3800:
        text = text[:3800] + "\n\n_[Resposta resumida. Acesse app.aji.com.br para a versão completa]_"
    
    return text
```

## Limitações Conhecidas

```
Evolution API NÃO é a API oficial do Meta
   - Conta pode ser banida pelo WhatsApp se detectada como automação
   - Para produção em escala (>100 números/dia): migrar para Meta Business API
   - No MVP: suficiente para validação

Para migração futura:
   - Meta Business API (oficial): Twilio ou 360dialog
   - Exige aprovação do Meta (processo de 2-4 semanas)
   - Tem custo por mensagem (~R$ 0,20–0,50)
   - Recomendado a partir de 200+ clientes ativos
```
