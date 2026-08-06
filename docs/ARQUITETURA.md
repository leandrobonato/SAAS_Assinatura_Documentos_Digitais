# Arquitetura — DocuFlow

## Visão geral

DocuFlow é dividido em dois serviços independentes que conversam via HTTP/JSON:

```
frontend/  React 19 + Vite — SPA (dashboard do remetente + página pública de assinatura)
backend/   FastAPI + SQLAlchemy + SQLite — API REST, geração/assinatura de PDF, agendador de lembretes
```

```
Remetente (autenticado)                    Signatário (sem login, via token)
        │                                             │
        ▼                                             ▼
  ┌─────────────┐        REST/JSON API        ┌───────────────┐
  │  React SPA  │ ───────────────────────────▶ │   FastAPI      │
  │  (Vite)     │ ◀─────────────────────────── │   backend      │
  └─────────────┘                              └───────┬────────┘
                                                          │
                                    ┌─────────────────────┼─────────────────────┐
                                    ▼                     ▼                     ▼
                              SQLite (SQLAlchemy)   storage/ (PDFs)      APScheduler
                                                     simula um bucket     (lembretes
                                                     S3 localmente        automáticos)
```

## Por que armazenamento local em vez de AWS S3 de verdade

O `backend/app/storage.py` expõe deliberadamente uma interface no estilo S3
(`put_object` / `get_object` / `delete_object`) implementada sobre o sistema
de arquivos local. Isso permite:

1. Rodar o projeto inteiro localmente, sem exigir credenciais de nuvem —
   consistente com os demais projetos do portfólio, que preferem dados
   sintéticos/mocks locais a depender de login externo.
2. Trocar para um S3 real depois só reescrevendo essas três funções — nenhum
   router ou lógica de negócio precisa mudar, já que consomem apenas essa
   interface.

## Fluxo de assinatura, passo a passo

1. **Upload** (`POST /documents`) — o remetente envia um PDF; o arquivo é
   validado (assinatura `%PDF`, parseável pelo `pypdf`) e salvo como
   `documents/{id}/original.pdf`.
2. **Signatários e campos** — o remetente adiciona signatários
   (`POST /documents/{id}/signers`) e define, por arrastar-e-soltar no
   frontend, onde cada um deve assinar (`PUT /documents/{id}/fields`). As
   coordenadas dos campos são armazenadas como frações relativas (0–1) da
   página, não em pixels — isso mantém a posição correta independentemente
   do zoom/resolução usados para renderizar o PDF depois.
3. **Envio** (`POST /documents/{id}/send`) — valida os limites do plano
   (ver abaixo), copia o PDF original para `documents/{id}/working.pdf` e
   envia um e-mail (real ou simulado) com um link único e não adivinhável
   por signatário (`/assinar/{token}`, token de 32 bytes via
   `secrets.token_urlsafe`).
4. **Assinatura pública** (`POST /public/sign/{token}`) — sem exigir login,
   o signatário desenha a assinatura em um `<canvas>`, digita o nome e
   confirma. O backend:
   - decodifica a imagem (PNG base64) e a sobrepõe no PDF de trabalho, nas
     posições dos campos daquele signatário (`pdf_utils.apply_signature`,
     via `reportlab` + `pypdf`);
   - grava IP e User-Agent do signatário nesse momento — essa é a prova de
     autenticidade, não uma assinatura criptográfica com certificado digital
     (ver seção "Limitações" abaixo);
   - registra um evento de auditoria (`AuditLog`).
5. **Conclusão automática** — quando o último signatário pendente assina, o
   backend gera uma **página de certificado** (hash SHA-256 do PDF
   original + nome/e-mail/horário/IP/user-agent de cada signatário),
   anexa essa página ao PDF assinado, calcula o hash SHA-256 do arquivo
   final e marca o documento como `completed`.

## Planos e diferenciação Free × Pro

| Recurso | Gratuito | Pro |
|---|---|---|
| Envios de documentos/mês | 5 | Ilimitado |
| Signatários por documento (envio em lote) | 1 | Ilimitado |
| Lembrete automático para quem não assinou | — | Sim |

- **"Envio em lote"** foi implementado como *múltiplos signatários em um
  único envio* (ex.: um contrato disparado para vários destinatários de
  uma vez), não como duplicação de um mesmo documento para destinatários
  independentes — mais simples de implementar corretamente e ainda cobre o
  caso de uso descrito no briefing original.
- O upgrade/downgrade de plano é **simulado** (`PATCH /auth/me/plan`) já
  que não há gateway de pagamento integrado nesta versão de portfólio —
  deixa o recurso Pro-only demonstrável de ponta a ponta.
- Os lembretes automáticos rodam via `APScheduler` a cada 12h
  (`backend/app/scheduler.py`) e também podem ser disparados manualmente em
  `POST /admin/run-reminders`, para não depender de esperar o intervalo
  real numa demonstração.

## Limitações conhecidas (honestidade de portfólio)

- **Não é uma assinatura digital com certificado ICP-Brasil/PKI.** O
  "certificado de autenticidade" gerado é uma prova por hash + trilha de
  auditoria (quem, quando, de qual IP), no mesmo espírito do que
  ferramentas como DocuSign oferecem no plano básico — não envolve uma
  autoridade certificadora nem carimbo de tempo de terceiros.
- **E-mail é simulado por padrão** (grava um `.eml` em
  `backend/storage/emails/` e imprime no console) quando `DOCUFLOW_SMTP_*`
  não está configurado — ver `docs/GUIA_INSTALACAO.md`.

## Decisões técnicas relevantes

- **`bcrypt` fixado em `4.0.1`** (`backend/requirements.txt`): o
  `passlib==1.7.4` (usado para hash de senha) faz um autoteste interno na
  primeira chamada que quebra com `bcrypt>=4.1` (`ValueError: password
  cannot be longer than 72 bytes...`), um problema conhecido de
  compatibilidade entre as duas bibliotecas. Fixar a versão evita o erro
  sem trocar de biblioteca de hashing.
- **Prefixo `DOCUFLOW_` em todas as variáveis de ambiente**
  (`backend/app/config.py`): evita colisão com variáveis genéricas que
  outras ferramentas/projetos na máquina de desenvolvimento possam já ter
  definido globalmente (ex.: uma `DATABASE_URL` de outro projeto Postgres
  sobrescrevendo silenciosamente o SQLite padrão deste projeto).
- **URL do SQLite construída via `sqlalchemy.engine.URL.create()`**, não
  por f-string: caminhos de projeto com acentos quebravam o parser de
  string do `create_engine` (`ArgumentError`) mesmo sendo um caminho
  válido no sistema de arquivos.
- **Campos de assinatura em coordenadas relativas (0–1)**, não pixels —
  desacopla a posição de onde o campo foi definido (frontend, resolução
  arbitrária) de onde é desenhado no PDF final (`reportlab`, coordenadas em
  pontos PDF, origem inferior-esquerda — a conversão top-left → bottom-left
  acontece em `pdf_utils.apply_signature`).
