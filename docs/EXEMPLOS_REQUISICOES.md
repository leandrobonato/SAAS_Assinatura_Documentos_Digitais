# Exemplos de requisições — API DocuFlow

Base URL local: `http://localhost:8000`. A documentação interativa (Swagger)
fica em `/docs`.

## Autenticação

### Criar conta

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ana Proprietária","email":"ana@example.com","password":"senha123"}'
```

Resposta (`access_token` é usado em todas as chamadas autenticadas abaixo):

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": 1, "name": "Ana Proprietária", "email": "ana@example.com", "plan": "free", "created_at": "..." }
}
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"senha123"}'
```

### Upgrade simulado de plano (Pro)

```bash
curl -X PATCH http://localhost:8000/auth/me/plan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro"}'
```

## Documentos

### Upload de um PDF

```bash
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Contrato de prestação de serviço" \
  -F "file=@contrato.pdf;type=application/pdf"
```

### Listar documentos do usuário

```bash
curl http://localhost:8000/documents -H "Authorization: Bearer $TOKEN"
```

### Adicionar um signatário

```bash
curl -X POST http://localhost:8000/documents/1/signers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"João Cliente","email":"joao@example.com"}'
```

### Definir campos de assinatura

Coordenadas são frações relativas (0–1) da página — `page_number` é
0-indexado.

```bash
curl -X PUT http://localhost:8000/documents/1/fields \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": [
      {"signer_id": 1, "page_number": 0, "x": 0.1, "y": 0.85, "width": 0.22, "height": 0.06}
    ]
  }'
```

### Enviar para assinatura

```bash
curl -X POST http://localhost:8000/documents/1/send -H "Authorization: Bearer $TOKEN"
```

Se o plano gratuito já tiver atingido o limite mensal (5 envios) ou o
documento tiver mais de 1 signatário, a resposta é `402 Payment Required`
com uma mensagem explicando o motivo.

### Baixar o PDF original / final assinado

```bash
curl http://localhost:8000/documents/1/original.pdf -H "Authorization: Bearer $TOKEN" -o original.pdf
curl http://localhost:8000/documents/1/final.pdf -H "Authorization: Bearer $TOKEN" -o assinado.pdf
```

### Trilha de auditoria

```bash
curl http://localhost:8000/documents/1/audit -H "Authorization: Bearer $TOKEN"
```

## Assinatura pública (sem autenticação — usa o token do link enviado por e-mail)

### Consultar o que o signatário precisa assinar

```bash
curl http://localhost:8000/public/sign/SEU_TOKEN_AQUI
```

```json
{
  "document_title": "Contrato de prestação de serviço",
  "signer_name": "João Cliente",
  "signer_status": "viewed",
  "total_pages": 2,
  "fields": [{"id": 1, "page_number": 0, "x": 0.1, "y": 0.85, "width": 0.22, "height": 0.06}],
  "other_signers_pending": []
}
```

### Baixar o PDF em progresso

```bash
curl http://localhost:8000/public/sign/SEU_TOKEN_AQUI/document.pdf -o documento.pdf
```

### Confirmar a assinatura

`signature_image` é um PNG em base64 (data URL), gerado a partir do
`<canvas>` de assinatura no frontend.

```bash
curl -X POST http://localhost:8000/public/sign/SEU_TOKEN_AQUI \
  -H "Content-Type: application/json" \
  -d '{
    "signature_image": "data:image/png;base64,iVBORw0KGgoAAAANSU...",
    "typed_name": "João Cliente"
  }'
```

Quando o último signatário pendente assina, a resposta já traz
`"status": "completed"` e o campo `final_hash` preenchido.

## Administração

### Disparar manualmente o envio de lembretes (normalmente roda a cada 12h)

```bash
curl -X POST http://localhost:8000/admin/run-reminders -H "Authorization: Bearer $TOKEN"
```

```json
{ "reminders_sent": 2 }
```
