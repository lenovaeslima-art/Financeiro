from datetime import date
import math

import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.cloud import firestore
from google.oauth2 import service_account
from streamlit.errors import StreamlitSecretNotFoundError


COLLECTION = "lancamentos"
SALARY_COLLECTION = "configuracoes_financeiras"
EXPENSE_GOAL_CENTS = 20_000
CATEGORIES = ["Alimentação", "Moradia", "Transporte", "Saúde", "Lazer", "Salário", "Outros"]


@st.cache_resource
def get_database() -> firestore.Client:
    firebase_config = dict(st.secrets["firebase"])
    credentials = service_account.Credentials.from_service_account_info(firebase_config)
    return firestore.Client(
        project=firebase_config["project_id"],
        credentials=credentials,
    )


def format_currency(cents: int) -> str:
    value = cents / 100
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def entry_data(description: str, category: str, kind: str, amount: float, entry_date: date) -> dict:
    return {
        "description": description.strip(),
        "category": category,
        "type": kind,
        "amount_cents": round(amount * 100),
        "date": entry_date.isoformat(),
    }


def expense_gauge(expense_cents: int) -> str:
    progress = min(max(expense_cents / EXPENSE_GOAL_CENTS, 0), 1)
    angle = math.pi * (1 - progress)
    needle_x = 100 + 68 * math.cos(angle)
    needle_y = 100 - 68 * math.sin(angle)
    circumference = math.pi * 80
    color = "#dc2626" if expense_cents >= EXPENSE_GOAL_CENTS else "#15803d"

    return f"""
        <div style="max-width: 360px; margin: auto; text-align: center;">
            <svg viewBox="0 0 200 125" role="img"
                 aria-label="Despesas de {format_currency(expense_cents)}; meta de R$ 200,00">
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none"
                      stroke="#e5e7eb" stroke-width="14" stroke-linecap="round"/>
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none"
                      stroke="{color}" stroke-width="14" stroke-linecap="round"
                      stroke-dasharray="{progress * circumference} {circumference}"/>
                <line x1="100" y1="100" x2="{needle_x}" y2="{needle_y}"
                      stroke="#1f2937" stroke-width="4" stroke-linecap="round"/>
                <circle cx="100" cy="100" r="7" fill="#1f2937"/>
                <text x="20" y="120" text-anchor="middle" font-size="10">R$ 0</text>
                <text x="180" y="120" text-anchor="middle" font-size="10">R$ 200</text>
                <text x="100" y="88" text-anchor="middle" font-size="17"
                      font-weight="bold" fill="{color}">{format_currency(expense_cents)}</text>
            </svg>
            <div style="color: {color}; font-weight: 600;">Meta de gastos: R$ 200,00</div>
        </div>
    """


st.set_page_config(page_title="Finanças pessoais", page_icon="💰", layout="wide")
st.title("💰 Finanças pessoais")
st.caption("Gerencie suas receitas e despesas.")

try:
    firebase_is_configured = "firebase" in st.secrets
except StreamlitSecretNotFoundError:
    firebase_is_configured = False

if not firebase_is_configured:
    st.error(
        "Configuração do Firebase não encontrada. Crie "
        "`.streamlit/secrets.toml` com as credenciais da conta de serviço. "
        "Veja o passo a passo no README."
    )
    st.stop()

try:
    database = get_database()
except (KeyError, ValueError) as error:
    st.error(f"A configuração do Firebase está incompleta ou inválida: {error}")
    st.stop()

st.subheader("Adicionar lançamento")
with st.form("new_entry", clear_on_submit=True):
    description = st.text_input("Descrição", max_chars=100)
    col1, col2, col3 = st.columns(3)
    with col1:
        kind = st.selectbox("Tipo", ["Despesa", "Receita"])
        category = st.selectbox("Categoria", CATEGORIES)
    with col2:
        amount = st.number_input("Valor (R$)", min_value=0.01, step=1.00, format="%.2f")
    with col3:
        entry_date = st.date_input("Data", value=date.today())
    submitted = st.form_submit_button("Adicionar lançamento", type="primary")

if submitted:
    if not description.strip():
        st.error("Informe uma descrição para o lançamento.")
    else:
        try:
            database.collection(COLLECTION).add(
                entry_data(description, category, kind, amount, entry_date)
            )
            st.success("Lançamento adicionado.")
            st.rerun()
        except GoogleAPIError as error:
            st.error(f"Não foi possível adicionar o lançamento: {error}")

st.divider()
st.subheader("Lançamentos")

try:
    entries = [
        {"id": document.id, **document.to_dict()}
        for document in database.collection(COLLECTION).stream()
    ]
except GoogleAPIError as error:
    st.error(f"Não foi possível carregar os lançamentos: {error}")
    st.stop()

entry_dates = []
for entry in entries:
    try:
        entry_dates.append(date.fromisoformat(entry.get("date", "")))
    except ValueError:
        continue

today = date.today()
filter_start_default = min(entry_dates, default=today)
filter_end_default = max(entry_dates, default=today)

st.markdown("#### Filtrar por período")
date_start_column, date_end_column = st.columns(2)
with date_start_column:
    date_start = st.date_input("Data inicial", value=filter_start_default)
with date_end_column:
    date_end = st.date_input("Data final", value=filter_end_default)

if date_start > date_end:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()

salary_document_id = f"salario_{date_start.isoformat()}_{date_end.isoformat()}"
salary_document = database.collection(SALARY_COLLECTION).document(salary_document_id)
try:
    salary_data = salary_document.get().to_dict() or {}
except GoogleAPIError as error:
    st.error(f"Não foi possível carregar o salário do período: {error}")
    st.stop()

st.markdown("#### Salário do período")
with st.form("salary_form"):
    salary_amount = st.number_input(
        "Valor total do salário (R$)",
        min_value=0.0,
        value=salary_data.get("salary_cents", 0) / 100,
        step=100.0,
        format="%.2f",
    )
    salary_submitted = st.form_submit_button("Salvar salário")

if salary_submitted:
    try:
        salary_document.set({"salary_cents": round(salary_amount * 100)})
        st.success("Salário do período salvo.")
        st.rerun()
    except GoogleAPIError as error:
        st.error(f"Não foi possível salvar o salário do período: {error}")

entries = [
    entry
    for entry in entries
    if not entry.get("date")
    or date_start.isoformat() <= entry["date"] <= date_end.isoformat()
]
entries.sort(key=lambda entry: entry.get("date", ""), reverse=True)
income = sum(entry.get("amount_cents", 0) for entry in entries if entry.get("type") == "Receita")
expenses = sum(entry.get("amount_cents", 0) for entry in entries if entry.get("type") == "Despesa")
salary_cents = salary_data.get("salary_cents", 0)
remaining_salary = salary_cents - expenses

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Receitas", format_currency(income))
metric2.metric("Despesas", format_currency(expenses))
metric3.metric("Saldo", format_currency(income - expenses))
metric4.metric("Salário restante", format_currency(remaining_salary))

st.markdown("#### Velocímetro da meta financeira")
st.markdown(expense_gauge(expenses), unsafe_allow_html=True)

expenses_by_category = {}
for entry in entries:
    if entry.get("type") == "Despesa":
        category = entry.get("category", "Outros")
        expenses_by_category[category] = (
            expenses_by_category.get(category, 0) + entry.get("amount_cents", 0)
        )

st.markdown("#### Gastos por categoria")
if expenses_by_category:
    chart_data = [
        {"Categoria": category, "Gastos (R$)": cents / 100}
        for category, cents in sorted(
            expenses_by_category.items(), key=lambda item: item[1], reverse=True
        )
    ]
    st.bar_chart(chart_data, x="Categoria", y="Gastos (R$)")
else:
    st.info("Não há despesas no período selecionado para exibir no gráfico.")

if not entries:
    st.info("Nenhum lançamento cadastrado ainda.")

for entry in entries:
    entry_id = entry["id"]
    label = (
        f'{entry.get("date", "Sem data")} · {entry.get("description", "Sem descrição")} · '
        f'{format_currency(entry.get("amount_cents", 0))}'
    )
    with st.expander(label):
        try:
            current_date = date.fromisoformat(entry.get("date", date.today().isoformat()))
        except ValueError:
            current_date = date.today()
            st.warning("A data salva não é válida; ao salvar, ela será atualizada.")

        with st.form(f"edit_{entry_id}"):
            edited_description = st.text_input(
                "Descrição",
                value=entry.get("description", ""),
                max_chars=100,
                key=f"description_{entry_id}",
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                current_type = entry.get("type", "Despesa")
                edited_type = st.selectbox(
                    "Tipo",
                    ["Despesa", "Receita"],
                    index=0 if current_type == "Despesa" else 1,
                    key=f"type_{entry_id}",
                )
                current_category = entry.get("category", "Outros")
                category_index = (
                    CATEGORIES.index(current_category)
                    if current_category in CATEGORIES
                    else CATEGORIES.index("Outros")
                )
                edited_category = st.selectbox(
                    "Categoria", CATEGORIES, index=category_index, key=f"category_{entry_id}"
                )
            with col2:
                edited_amount = st.number_input(
                    "Valor (R$)",
                    min_value=0.01,
                    value=max(entry.get("amount_cents", 1) / 100, 0.01),
                    step=1.00,
                    format="%.2f",
                    key=f"amount_{entry_id}",
                )
            with col3:
                edited_date = st.date_input(
                    "Data", value=current_date, key=f"date_{entry_id}"
                )

            save, delete = st.columns(2)
            with save:
                save_clicked = st.form_submit_button("Salvar alterações", type="primary")
            with delete:
                delete_clicked = st.form_submit_button("Excluir lançamento")

        if save_clicked:
            if not edited_description.strip():
                st.error("A descrição não pode ficar vazia.")
            else:
                try:
                    database.collection(COLLECTION).document(entry_id).update(
                        entry_data(
                            edited_description,
                            edited_category,
                            edited_type,
                            edited_amount,
                            edited_date,
                        )
                    )
                    st.success("Lançamento atualizado.")
                    st.rerun()
                except GoogleAPIError as error:
                    st.error(f"Não foi possível atualizar o lançamento: {error}")

        if delete_clicked:
            try:
                database.collection(COLLECTION).document(entry_id).delete()
                st.success("Lançamento excluído.")
                st.rerun()
            except GoogleAPIError as error:
                st.error(f"Não foi possível excluir o lançamento: {error}")
