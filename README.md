# Gestão financeira pessoal

Aplicação simples em Streamlit para cadastrar, consultar, editar e excluir receitas e despesas no Cloud Firestore.

A listagem, os totais, o gráfico de barras de gastos por categoria e o salário podem ser consultados por data inicial e final, incluindo as datas selecionadas. O salário é salvo para cada intervalo escolhido, e o valor restante é calculado após descontar as despesas desse período. O velocímetro de gastos fica vermelho ao atingir R$ 200,00 em despesas.

## Configuração do Firebase

1. No console do Firebase, confirme que o Cloud Firestore está ativado e crie o banco de dados padrão, se ainda não existir.
2. Nas configurações do projeto, crie uma chave JSON de uma conta de serviço com acesso ao Firestore.
3. Crie `.streamlit/secrets.toml` na raiz do projeto e copie os campos da chave JSON para a seção abaixo. Não envie esse arquivo para o Git.

```toml
[firebase]
type = "service_account"
project_id = "id-do-seu-projeto"
private_key_id = "id-da-chave"
private_key = """-----BEGIN PRIVATE KEY-----
COLE_A_CHAVE_PRIVADA_DA_CONTA_DE_SERVICO
-----END PRIVATE KEY-----\n"""
client_email = "conta-de-servico@id-do-seu-projeto.iam.gserviceaccount.com"
client_id = "id-do-cliente"
token_uri = "https://oauth2.googleapis.com/token"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "url-do-certificado-da-conta"
```

Use os valores reais da chave JSON baixada. O campo `private_key` deve preservar as quebras de linha da chave. Nunca compartilhe ou versione suas credenciais.

## Executar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

O aplicativo usa o banco de dados padrão do Firestore (`(default)`) e cria a coleção `lancamentos` na primeira gravação. Valores são armazenados em centavos inteiros para evitar imprecisão monetária.
