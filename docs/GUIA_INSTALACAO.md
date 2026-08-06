# Guia de instalação — DocuFlow

## Pré-requisitos

- **Python 3.11+**
- **Node.js 18+** (recomendado 20+)
- Nenhuma conta de nuvem é necessária — o projeto roda 100% localmente
  (armazenamento de PDFs em disco, e-mail simulado por padrão).

## 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Git Bash) / Linux / macOS
source .venv/Scripts/activate   # Git Bash no Windows
source .venv/bin/activate       # Linux / macOS
```

Instale as dependências e configure o `.env`:

```bash
pip install -r requirements-dev.txt   # inclui pytest, além das deps de produção
cp .env.example .env                  # ajuste se necessário — os valores padrão já funcionam
```

Rode os testes automatizados (5 testes cobrindo o fluxo completo, limites de
plano e lembretes):

```bash
pytest -v
```

Suba o servidor:

```bash
uvicorn app.main:app --reload --port 8000
```

A documentação interativa da API fica em `http://localhost:8000/docs`.

## 2. Frontend (React + Vite)

Em outro terminal:

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL já aponta para http://localhost:8000
npm run dev
```

Acesse `http://localhost:5173`.

## 3. Usando o sistema

1. Crie uma conta em `/registro`.
2. No dashboard, clique em **"+ Novo documento"** e envie um PDF.
3. Na tela do documento, adicione um ou mais signatários (nome + e-mail).
4. **Arraste o card do signatário até a posição desejada no PDF** para
   posicionar o campo de assinatura dele. É possível reposicionar
   arrastando o campo já criado, ou removê-lo pelo "✕".
5. Clique em **"Enviar para assinatura"**.
6. Como não há SMTP configurado por padrão, o "e-mail" com o link de
   assinatura é salvo em `backend/storage/emails/*.eml` — abra o arquivo
   mais recente para pegar o link (`/assinar/{token}`).
7. Abra o link (pode ser em uma aba anônima, simulando o signatário sem
   login), desenhe a assinatura, digite o nome, aceite os termos e
   confirme.
8. Quando todos os signatários assinarem, o documento aparece como
   **Concluído**, com hash SHA-256, trilha de auditoria e botão para
   baixar o PDF final (que inclui uma página de certificado de
   autenticidade anexada).

## 4. Testando o plano Pro (lembretes automáticos + envio em lote)

O upgrade de plano é simulado (sem gateway de pagamento) para permitir
testar os recursos Pro-only:

1. No dashboard, clique em **"Fazer upgrade para o Pro"**.
2. Agora é possível adicionar mais de um signatário por documento
   (envio em lote).
3. Para não esperar o agendador automático (que roda a cada 12h), dispare o
   envio de lembretes manualmente:

```bash
curl -X POST http://localhost:8000/admin/run-reminders \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

Lembretes só são enviados para documentos enviados há mais de
`DOCUFLOW_REMINDER_AFTER_DAYS` dias (padrão: 2) — em uma demonstração real,
ajuste essa variável no `.env` para um valor menor, ou edite manualmente
`sent_at` no banco para testar sem esperar.

## 5. Configurando SMTP real (opcional)

Por padrão, os e-mails são simulados. Para enviar e-mails reais, preencha
no `backend/.env`:

```
DOCUFLOW_SMTP_HOST=smtp.seuservidor.com
DOCUFLOW_SMTP_PORT=587
DOCUFLOW_SMTP_USER=seu-usuario
DOCUFLOW_SMTP_PASSWORD=sua-senha
DOCUFLOW_SMTP_FROM=no-reply@seudominio.com
```

## Solução de problemas

- **`ValueError: password cannot be longer than 72 bytes...` ao
  registrar/logar** — incompatibilidade conhecida entre `passlib==1.7.4` e
  `bcrypt>=4.1`. O `requirements.txt` já fixa `bcrypt==4.0.1`; se você
  atualizou o bcrypt manualmente, reinstale a versão fixada:
  `pip install "bcrypt==4.0.1"`.
- **Erro `Could not parse SQLAlchemy URL` ao subir o backend** — geralmente
  indica que uma variável de ambiente `DATABASE_URL` genérica (de outra
  ferramenta/projeto na máquina) está sobrescrevendo o padrão do projeto.
  Todas as configurações do DocuFlow usam o prefixo `DOCUFLOW_` (ex.:
  `DOCUFLOW_DATABASE_URL`) exatamente para evitar esse tipo de colisão —
  confirme com `env | grep -i database_url` (Bash) ou
  `Get-ChildItem Env: | Where-Object Name -match database_url`
  (PowerShell) que não há uma variável `DATABASE_URL` (sem o prefixo)
  interferindo.
- **CORS bloqueado no navegador** — o backend já libera
  `http://localhost:5173` e `http://127.0.0.1:5173` por padrão
  (`backend/app/main.py`). Se você mudar a porta do frontend, adicione a
  nova origem em `allow_origins`.
