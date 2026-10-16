import json
import os
from datetime import date, datetime
from pathlib import Path

import firebase_admin
import pandas as pd
import streamlit as st
from firebase_admin import credentials, firestore
from streamlit.errors import StreamlitSecretNotFoundError

PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
COLLECTION_NAME = "despesas"
CATEGORIES = [
    "Moradia",
    "Alimentacao",
    "Transporte",
    "Saude",
    "Educacao",
    "Lazer",
    "Contas",
    "Compras",
    "Outros",
]

st.set_page_config(page_title="Despesas", page_icon="R$", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --ink: #202b25;
        --muted: #65736b;
        --green: #177245;
        --green-soft: #eaf4ed;
        --line: #e3e9e4;
        --surface: #ffffff;
    }
    .stApp { background: #f5f7f4; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(245, 247, 244, .92); }
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px 18px;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    div.stButton > button[kind="primary"] {
        background: var(--green);
        border-color: var(--green);
    }
    div[data-testid="stSidebar"] { background: #eef3ee; }
    h1, h2, h3 { color: var(--ink); }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_streamlit_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default


def get_firestore_client():
    """Inicializa o Firebase usando Streamlit Secrets, JSON ou ADC."""
    if firebase_admin._apps:
        app = firebase_admin.get_app()
    else:
        raw_credentials = os.getenv("FIREBASE_CREDENTIALS_JSON")
        streamlit_service_account = get_streamlit_secret("firebase_service_account")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        app_directory = Path(__file__).parent
        local_key = app_directory / "serviceAccountKey.json"
        if not local_key.exists():
            matching_keys = sorted(app_directory.glob("*-firebase-adminsdk-*.json"))
            if len(matching_keys) == 1:
                local_key = matching_keys[0]
            elif len(matching_keys) > 1:
                raise RuntimeError("Mais de uma chave Firebase encontrada; configure GOOGLE_APPLICATION_CREDENTIALS.")

        if raw_credentials:
            service_account = json.loads(raw_credentials)
            credential = credentials.Certificate(service_account)
        elif streamlit_service_account and streamlit_service_account.get("private_key"):
            credential = credentials.Certificate(dict(streamlit_service_account))
        elif credentials_path:
            credential = credentials.Certificate(credentials_path)
        elif local_key.exists():
            credential = credentials.Certificate(str(local_key))
        else:
            credential = credentials.ApplicationDefault()

        project_id = (
            PROJECT_ID
            or get_streamlit_secret("FIREBASE_PROJECT_ID")
            or getattr(credential, "project_id", None)
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or "despesas-2760c"
        )
        app = firebase_admin.initialize_app(
            credential,
            {"projectId": project_id},
        )

    return firestore.client(app=app)


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return date.today()


def format_brl(value):
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def fetch_expenses(client):
    items = []
    for document in client.collection(COLLECTION_NAME).stream():
        item = document.to_dict()
        item["id"] = document.id
        item["data"] = as_date(item.get("data"))
        item["valor"] = float(item.get("valor", 0))
        items.append(item)
    return sorted(items, key=lambda item: (item["data"], item.get("criado_em", "")), reverse=True)


st.title("Despesas")
st.caption("Controle simples das suas despesas, em um só lugar.")

try:
    db = get_firestore_client()
    expenses = fetch_expenses(db)
except Exception as error:
    st.error("Nao foi possivel conectar ao Firebase.")
    st.markdown(
        "Configure as credenciais seguindo o [README](README.md) e confirme que o "
        "Firestore esta ativado no projeto `despesas`."
    )
    with st.expander("Detalhes tecnicos"):
        st.code(str(error))
    st.stop()

current_month = date.today().strftime("%Y-%m")
month_expenses = [item for item in expenses if item["data"].strftime("%Y-%m") == current_month]
month_total = sum(item["valor"] for item in month_expenses)
all_total = sum(item["valor"] for item in expenses)

metric_month, metric_count, metric_all = st.columns(3)
metric_month.metric("Total deste mes", format_brl(month_total))
metric_count.metric("Lancamentos neste mes", len(month_expenses))
metric_all.metric("Total registrado", format_brl(all_total))

st.divider()

with st.sidebar:
    st.header("Nova despesa")
    with st.form("new_expense", clear_on_submit=True):
        description = st.text_input("Descricao", placeholder="Ex.: Mercado")
        amount = st.number_input("Valor (R$)", min_value=0.01, step=1.0, format="%.2f")
        expense_date = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        category = st.selectbox("Categoria", CATEGORIES)
        notes = st.text_input("Observacoes", placeholder="Opcional")
        add_expense = st.form_submit_button("Adicionar despesa", type="primary", use_container_width=True)

    if add_expense:
        if not description.strip():
            st.warning("Informe uma descricao para a despesa.")
        else:
            db.collection(COLLECTION_NAME).add(
                {
                    "descricao": description.strip(),
                    "valor": round(amount, 2),
                    "data": expense_date.isoformat(),
                    "categoria": category,
                    "observacoes": notes.strip(),
                    "criado_em": datetime.now().isoformat(timespec="seconds"),
                }
            )
            st.rerun()

st.subheader("Lancamentos")
filter_months = sorted({item["data"].strftime("%Y-%m") for item in expenses}, reverse=True)
filter_columns = st.columns([1, 1, 2])
selected_month = filter_columns[0].selectbox("Mes", ["Todos"] + filter_months)
filter_categories = ["Todas"] + sorted({item.get("categoria", "Outros") for item in expenses})
selected_category = filter_columns[1].selectbox("Categoria", filter_categories)
filter_columns[2].write("")

visible_expenses = expenses
if selected_month != "Todos":
    visible_expenses = [item for item in visible_expenses if item["data"].strftime("%Y-%m") == selected_month]
if selected_category != "Todas":
    visible_expenses = [item for item in visible_expenses if item.get("categoria") == selected_category]

if visible_expenses:
    table = pd.DataFrame(
        [
            {
                "Data": item["data"].strftime("%d/%m/%Y"),
                "Descricao": item.get("descricao", ""),
                "Categoria": item.get("categoria", "Outros"),
                "Valor": format_brl(item["valor"]),
                "Observacoes": item.get("observacoes", ""),
            }
            for item in visible_expenses
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)
else:
    st.info("Nenhuma despesa encontrada para esses filtros.")

with st.expander("Editar ou excluir lancamento"):
    if not expenses:
        st.caption("Adicione uma despesa para habilitar a edicao.")
    else:
        expense_by_id = {item["id"]: item for item in expenses}
        selected_id = st.selectbox(
            "Selecione uma despesa",
            options=list(expense_by_id),
            format_func=lambda expense_id: (
                f"{expense_by_id[expense_id]['data'].strftime('%d/%m/%Y')} - "
                f"{expense_by_id[expense_id].get('descricao', 'Sem descricao')} - "
                f"{format_brl(expense_by_id[expense_id]['valor'])}"
            ),
        )
        selected_expense = expense_by_id[selected_id]
        edit_categories = list(CATEGORIES)
        if selected_expense.get("categoria") not in edit_categories:
            edit_categories.append(selected_expense["categoria"])

        with st.form(f"edit_expense_{selected_id}"):
            edited_description = st.text_input("Descricao", value=selected_expense.get("descricao", ""))
            edited_amount = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                value=max(0.01, selected_expense["valor"]),
                step=1.0,
                format="%.2f",
            )
            edited_date = st.date_input("Data", value=selected_expense["data"], format="DD/MM/YYYY")
            edited_category = st.selectbox(
                "Categoria",
                edit_categories,
                index=edit_categories.index(selected_expense.get("categoria", "Outros")),
            )
            edited_notes = st.text_input("Observacoes", value=selected_expense.get("observacoes", ""))
            save_changes = st.form_submit_button("Salvar alteracoes", type="primary")

        if save_changes:
            if not edited_description.strip():
                st.warning("Informe uma descricao para a despesa.")
            else:
                db.collection(COLLECTION_NAME).document(selected_id).update(
                    {
                        "descricao": edited_description.strip(),
                        "valor": round(edited_amount, 2),
                        "data": edited_date.isoformat(),
                        "categoria": edited_category,
                        "observacoes": edited_notes.strip(),
                        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                st.rerun()

        confirm_delete = st.checkbox("Confirmo que quero excluir esta despesa", key=f"confirm_{selected_id}")
        if st.button("Excluir despesa", disabled=not confirm_delete, key=f"delete_{selected_id}"):
            db.collection(COLLECTION_NAME).document(selected_id).delete()
            st.rerun()
