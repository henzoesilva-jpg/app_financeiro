# Controle de despesas

App em Streamlit para cadastrar, consultar, filtrar, editar e excluir despesas no Cloud Firestore do projeto Firebase `despesas` (ID `despesas-2760c`).

## Preparar o Firebase

1. No [Firebase Console](https://console.firebase.google.com/), abra o projeto `despesas` (ID `despesas-2760c`) e crie/ative o banco **Cloud Firestore**. Escolha a regiao desejada; ela nao pode ser alterada depois da criacao.
2. Em **Configuracoes do projeto > Contas de servico**, gere uma chave privada para uma conta de servico. Guarde o JSON fora do repositorio.
3. Configure uma credencial de conta de servico com permissao para ler e gravar no Firestore. O SDK administrativo ignora as regras de seguranca do cliente.

Para desenvolvimento local, preencha `.streamlit/secrets.toml` com os campos da conta de servico. O arquivo ja esta excluido do Git. Como alternativa, configure o caminho do JSON no PowerShell:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\caminho\seguro\despesas.json"
$env:FIREBASE_PROJECT_ID="despesas-2760c"
```

O app tambem detecta automaticamente um unico arquivo `*-firebase-adminsdk-*.json` na raiz do projeto. Preferencialmente, guarde a chave fora do repositorio; nunca envie a chave para o Git.

## Publicar no Streamlit Community Cloud

1. Envie o codigo do app para um repositorio GitHub. Nao inclua a chave JSON nem `.streamlit/secrets.toml`.
2. Em [share.streamlit.io](https://share.streamlit.io/), crie um app e selecione o repositorio, branch e `app.py`.
3. Abra **App settings > Secrets** e cole o conteudo completo do arquivo local `.streamlit/secrets.toml`, que ja foi preenchido com a conta de servico. Nao envie esse arquivo ao repositorio. O bloco abaixo mostra a estrutura caso precise configurar Secrets em outra maquina; nesse caso, substitua os valores `COLE_...` pelos campos equivalentes do JSON.

```toml
FIREBASE_PROJECT_ID = "despesas-2760c"

[firebase_service_account]
type = "service_account"
project_id = "despesas-2760c"
private_key_id = "COLE_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nCOLE_A_CHAVE_PRIVADA\n-----END PRIVATE KEY-----\n"
client_email = "COLE_CLIENT_EMAIL"
client_id = "COLE_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "COLE_CLIENT_X509_CERT_URL"
universe_domain = "googleapis.com"
```

O app le `[firebase_service_account]` e `FIREBASE_PROJECT_ID` tanto do arquivo local quanto dos Secrets do Streamlit Cloud. O conteudo inserido em **App settings > Secrets** deve ser TOML, nao o JSON inteiro. A chave privada e sensivel e nao deve ser compartilhada nem commitada.

## Instalar e executar

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

O app cria a colecao `despesas` automaticamente ao salvar o primeiro registro. Cada documento contem `descricao`, `valor`, `data`, `categoria`, `observacoes` e `criado_em`; edicoes tambem registram `atualizado_em`.

## Regras do Firestore

O app acessa o Firestore pelo SDK administrativo no servidor. As regras em `firestore.rules` bloqueiam acesso direto pelo SDK cliente, sem impedir o acesso do app. Para publicar as regras, instale/tenha o Firebase CLI autenticado e execute:

```powershell
firebase use despesas-2760c
firebase deploy --only firestore:rules
```

Nao publique regras permissivas para contornar erros de credencial. Corrija a configuracao da conta de servico.
