# Evolution API — Setup e Integração

## Decisão de Stack

**Evolution API** (recomendada sobre Twilio para o AJI) porque:
- Open source, sem custo por mensagem
- Auto-hospedado (Railway ou VPS)
- Suporte a WhatsApp Business API não oficial
- Ideal para MVP antes de ter aprovação Meta oficial

Para produção em escala: migrar para **Twilio / Meta Business API oficial**.

## WhatsApp Service

```python
# app/services/whatsapp.py

import httpx

class WhatsAppService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = "aji-prod"
    
    async def send(self, phone: str, message: str):
        """Enviar mensagem de texto"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={
                    "number": phone,
                    "text": message,
                    "delay": 1200  # Simular digitação (ms)
                }
            )
    
    async def send_typing(self, phone: str, duration_ms: int = 3000):
        """Mostrar 'digitando...' enquanto processa"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/chat/sendPresence/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": phone, "presence": "composing", "delay": duration_ms}
            )
```

## Configuração

```bash
# Variáveis necessárias
EVOLUTION_API_URL=https://evolution.seudominio.com
EVOLUTION_API_KEY=sua-api-key
```
