# Background Tasks (Celery)

## Tasks Principais

```python
# app/workers/tasks.py

@celery.task(bind=True, max_retries=3)
def process_document_ingestion(self, document_id: str, tenant_id: str):
    """Ingestão assíncrona de documentos para base privada"""
    try:
        doc = DocumentRepository.get(document_id)
        ingester = LegalDocumentIngester(doc_type=doc.type)
        ingester.ingest(doc.content, doc.metadata, tenant_id)
        DocumentRepository.update(document_id, {"status": "indexed"})
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery.task
def send_monthly_usage_report(tenant_id: str):
    """Relatório mensal de uso por email"""
    stats = UsageRepository.get_monthly_stats(tenant_id)
    EmailService.send_usage_report(stats)

@celery.task  
def check_trial_expiration():
    """Roda diariamente: notifica tenants com trial expirando"""
    expiring = TenantRepository.get_trials_expiring_in(days=3)
    for tenant in expiring:
        EmailService.send_trial_expiring(tenant)
```

## Regras

1. Toda task DEVE ter `max_retries` definido para evitar loops infinitos
2. Usar `countdown` exponencial para retries (60s, 120s, 240s)
3. Tasks de ingestão DEVEM validar `tenant_id` antes de processar
4. Logs de tasks NUNCA devem conter dados sensíveis (CNPJ, bank_data)
