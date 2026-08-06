# DocuFlow

**Assinatura digital de documentos, sem a fatura do DocuSign.**

DocuFlow é uma plataforma SaaS para enviar contratos em PDF, posicionar
campos de assinatura por arrastar-e-soltar e receber de volta o documento
assinado — com hash SHA-256 e trilha de auditoria (IP + horário) como prova
de autenticidade. Pensado para autônomos, corretores, advogados e
prestadores de serviço que precisam formalizar acordos rapidamente sem
pagar por um plano corporativo de assinatura eletrônica.

> Projeto de portfólio full-stack: back-end em Python/FastAPI, front-end em
> React, com o fluxo de assinatura ponta a ponta funcional — upload,
> posicionamento de campos, envio, assinatura pública e geração do PDF
> final com certificado de autenticidade.

---

## Funcionalidades

- **Upload de PDF** e definição de campos de assinatura por **arrastar e
  soltar**, diretamente sobre a pré-visualização do documento.
- **Múltiplos signatários** por documento, cada um com seu próprio link de
  assinatura (sem necessidade de criar conta).
- **Assinatura eletrônica via canvas**, com nome digitado e aceite de
  termos, registrando **IP e horário** como prova de autenticidade.
- **Hash SHA-256** do documento original e do arquivo final, com uma
  **página de certificado de autenticidade** anexada automaticamente ao
  PDF assinado.
- **Trilha de auditoria completa** por documento (enviado, visualizado,
  assinado, concluído).
- **Plano gratuito** com 5 envios/mês e 1 signatário por documento.
- **Plano Pro** com envio em lote (múltiplos signatários por envio) e
  **lembrete automático** por e-mail para quem ainda não assinou.

## Stack técnica

| Camada | Tecnologia |
|---|---|
| Front-end | React 19, Vite, React Router, `react-pdf` |
| Back-end | FastAPI, SQLAlchemy, SQLite |
| Geração/assinatura de PDF | `pypdf` + `reportlab` |
| Autenticação | JWT (`python-jose`) + `passlib`/bcrypt |
| Agendamento | APScheduler (lembretes automáticos) |
| Armazenamento | Sistema de arquivos local, atrás de uma interface no estilo S3 (troca fácil por AWS S3 real) |

## Como rodar o projeto

Guia completo em [`docs/GUIA_INSTALACAO.md`](docs/GUIA_INSTALACAO.md).
Resumo:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env
pytest -v                 # 5 testes cobrindo o fluxo completo
uvicorn app.main:app --reload --port 8000

# Frontend (em outro terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Acesse `http://localhost:5173`.

## Documentação

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) — decisões técnicas, fluxo
  de assinatura passo a passo, limitações conhecidas.
- [`docs/GUIA_INSTALACAO.md`](docs/GUIA_INSTALACAO.md) — passo a passo
  completo de instalação e uso, incluindo o fluxo de teste do plano Pro.
- [`docs/EXEMPLOS_REQUISICOES.md`](docs/EXEMPLOS_REQUISICOES.md) —
  exemplos de requisições `curl` para todos os endpoints principais da
  API.

## Estrutura do projeto

```
backend/
  app/
    routers/        # auth, documents, signing (público), admin
    models.py        # User, Document, Signer, SignatureField, AuditLog
    pdf_utils.py      # overlay de assinatura, hash, certificado
    reminders.py       # lembretes automáticos (plano Pro)
    storage.py           # abstração de armazenamento (S3-like, local)
  tests/               # pytest — fluxo completo, limites de plano, lembretes
frontend/
  src/
    pages/            # Dashboard, DocumentEditor, PublicSign, Login/Registro
    components/         # editor drag-and-drop, canvas de assinatura, etc.
data/
  contrato_exemplo.pdf   # PDF de exemplo para testar o fluxo rapidamente
docs/                    # documentação técnica detalhada
```

## Importante

Este é um projeto de portfólio. O "certificado de autenticidade" gerado é
uma prova por **hash + trilha de auditoria** (quem assinou, quando, de qual
IP) — não substitui uma assinatura digital com certificado ICP-Brasil/PKI
para documentos que exijam validade jurídica plena nesse nível. Detalhes em
[`docs/ARQUITETURA.md`](docs/ARQUITETURA.md#limitações-conhecidas-honestidade-de-portfólio).

---

Desenvolvido por [Leandro Miozzo Bonato](https://github.com/leandrobonato).
