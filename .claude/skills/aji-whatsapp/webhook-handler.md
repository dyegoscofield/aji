# Webhook Handler e Processamento de Mensagens

## Fluxo de Autenticação via WhatsApp

```
Usuário envia mensagem → AJI
          ↓
Verificar se número está cadastrado
          ↓
    NÃO                  SIM
     ↓                    ↓
Pedir CNPJ          Verificar plano ativo
     ↓                    ↓
Validar CNPJ        Processar consulta
     ↓                    ↓
Criar sessão        Retornar resposta
```

## Webhook Handler

```python
# app/api/v1/whatsapp.py

from fastapi import APIRouter, Request, HTTPException
from app.services.whatsapp import WhatsAppService
from app.services.aji import AJIService

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])

@router.post("/")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    
    if payload.get('event') != 'messages.upsert':
        return {"status": "ignored"}
    
    message = payload['data']
    
    if message.get('key', {}).get('fromMe'):
        return {"status": "ignored"}
    
    phone = message['key']['remoteJid'].replace('@s.whatsapp.net', '')
    text = message.get('message', {}).get('conversation', '')
    
    if not text:
        return {"status": "ignored"}
    
    background_tasks.add_task(
        process_whatsapp_message,
        phone=phone, text=text, db=db
    )
    
    return {"status": "queued"}

async def process_whatsapp_message(phone: str, text: str, db: AsyncSession):
    wa = WhatsAppService()
    user = await UserRepository.get_by_phone(db, phone)
    
    if not user:
        await handle_new_user(wa, phone, text, db)
        return
    
    tenant = await TenantRepository.get(db, user.tenant_id)
    
    if tenant.status not in ['trial', 'active']:
        await wa.send(phone, "Sua assinatura AJI está suspensa. Acesse app.aji.com.br para regularizar.")
        return
    
    if tenant.plan == 'essencial':
        count = await MessageRepository.count_this_month(db, tenant.id)
        if count >= 30:
            await wa.send(phone, 
                "Você atingiu o limite de 30 consultas mensais do plano Essencial.\n\n"
                "Para continuar, faça upgrade: app.aji.com.br/planos"
            )
            return
    
    aji = AJIService()
    response = await aji.process(
        query=text,
        tenant=tenant,
        channel='whatsapp',
        conversation_history=await get_whatsapp_history(db, phone)
    )
    
    formatted = format_for_whatsapp(response.content)
    await wa.send(phone, formatted)
    await save_whatsapp_exchange(db, tenant.id, user.id, text, response)
```

## Segurança WhatsApp

```python
WHATSAPP_SECURITY = {
    'validar_webhook': True,
    'rate_limit_por_numero': '10/min',
    'bloquear_grupos': True,
    'horario_atendimento': 'always',
    'log_todas_mensagens': True,
    'pii_mascarado_logs': True,
}
```

## Métricas WhatsApp

```python
WA_METRICS = [
    'mensagens_recebidas_dia',
    'tempo_resposta_medio_segundos',
    'taxa_onboarding_sucesso',
    'consultas_via_whatsapp_vs_web',
    'erros_parsing_cnpj',
    'mensagens_fora_escopo',
]
```
