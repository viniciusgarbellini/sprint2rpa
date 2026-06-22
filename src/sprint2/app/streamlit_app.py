"""Interface operacional da Sprint 2 (Streamlit).

Entrega o "Protótipo de Interface": login com papéis, navegação hierárquica
(planta → área → ativo), busca por TAG, visualização dos valores atuais dos
sensores e séries temporais do histórico, mapeamento Ativo-TAG-Localização e
auditoria das automações RPA. Admin pode disparar as RPAs sob demanda.

Executar:
    streamlit run src/sprint2/app/streamlit_app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from sprint2.app.auth import authenticate
from sprint2.models import AccessEvent
from sprint2.repository import Repository

st.set_page_config(page_title="Sprint 2 — Monitor Operacional", layout="wide")

repo = Repository()


@st.cache_resource
def _bootstrap() -> bool:
    """Garante que o schema exista (idempotente, roda uma vez por processo)."""
    from sprint2.db import apply_migrations

    apply_migrations()
    return True


try:
    _bootstrap()
except Exception as exc:  # banco ainda subindo / indisponível
    st.warning(f"Banco indisponível no momento ({exc}). Recarregue em instantes.")


# ---------------------------------------------------------------------------
# Auditoria de acesso (sem spam: só registra quando o alvo muda)
# ---------------------------------------------------------------------------
def audit(action: str, target: str | None = None) -> None:
    auth = st.session_state.get("auth")
    if not auth:
        return
    key = f"_audited::{action}::{target}"
    if st.session_state.get(key):
        return
    try:
        repo.log_access(
            AccessEvent(username=auth["username"], role=auth["role"],
                        action=action, target=target)
        )
        st.session_state[key] = True
    except Exception:
        pass  # auditoria nunca quebra a navegação


# ---------------------------------------------------------------------------
# Tela de login
# ---------------------------------------------------------------------------
def login_screen() -> None:
    st.title("🔐 Monitor Operacional — Acesso")
    st.caption("Sprint 2 · Digital Twin de motores industriais")
    with st.form("login"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        role = authenticate(username, password)
        if role:
            st.session_state["auth"] = {"username": username.strip(), "role": role}
            try:
                repo.log_access(AccessEvent(username=username.strip(), role=role,
                                            action="LOGIN"))
            except Exception:
                pass
            st.rerun()
        else:
            try:
                repo.log_access(AccessEvent(username=(username or "?").strip(),
                                            role="-", action="LOGIN_FAIL"))
            except Exception:
                pass
            st.error("Usuário ou senha inválidos.")
    st.info("Demo: **operador / operador123** ou **admin / admin123**")


# ---------------------------------------------------------------------------
# Métricas atuais + séries temporais de um ativo
# ---------------------------------------------------------------------------
def _fmt(value, suffix: str = "", nd: int = 1) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{nd}f}{suffix}"


def render_asset(tag: str) -> None:
    asset = repo.asset_full(tag)
    if asset is None:
        st.warning(f"Ativo {tag} não encontrado.")
        return

    audit("VIEW_ASSET", tag)

    status_emoji = {"ACTIVE": "🟢", "MAINTENANCE": "🟡", "INACTIVE": "🔴"}.get(
        asset.get("status", ""), "⚪"
    )
    st.subheader(f"{status_emoji} {asset['tag']} — {asset['name']}")

    # Localização (mapeamento Ativo-TAG-Localização)
    plant = asset.get("plant_name") or "—"
    area = asset.get("area_name") or "—"
    st.markdown(f"**Localização:** 🏭 {plant}  ›  🗂️ {area}")

    last = repo.latest_reading(tag)
    st.markdown("#### Valores atuais dos sensores")
    if not last:
        st.info("Sem leituras registradas para este ativo ainda.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tensão", _fmt(last.get("voltage_v"), " V", 0))
        c2.metric("Corrente", _fmt(last.get("current_a"), " A"))
        c3.metric("Temperatura", _fmt(last.get("temperature_c"), " °C"))
        c4.metric("Rotação", _fmt(last.get("rpm"), " rpm", 0))
        c5.metric("Vibração", _fmt(last.get("vibration_mm_s"), " mm/s", 2))
        st.caption(f"Última leitura: {last.get('measured_at')} · "
                   f"qualidade={_fmt(last.get('quality_score'), '', 2)}")

    # Dados de placa (cadastro técnico) vs nominais
    with st.expander("📋 Dados de placa (cadastro técnico do ativo)"):
        cols = st.columns(4)
        cols[0].write(f"**Fabricante:** {asset.get('manufacturer') or '—'}")
        cols[1].write(f"**Modelo:** {asset.get('model') or '—'}")
        cols[2].write(f"**Pot. nominal:** {_fmt(asset.get('rated_power_kw'), ' kW')}")
        cols[3].write(f"**RPM nominal:** {_fmt(asset.get('rated_rpm'), '', 0)}")
        cols2 = st.columns(4)
        cols2[0].write(f"**Tensão nom.:** {_fmt(asset.get('rated_voltage_v'), ' V', 0)}")
        cols2[1].write(f"**Corrente nom.:** {_fmt(asset.get('rated_current_a'), ' A')}")

        nps = repo.nameplate_history(tag)
        if nps:
            st.caption("Proveniência (extração da placa):")
            st.dataframe(pd.DataFrame(nps), hide_index=True,
                         use_container_width=True)

    # Séries temporais
    st.markdown("#### Histórico (últimas 24h)")
    history = repo.readings_history(tag, hours=24)
    if not history:
        st.info("Sem histórico nas últimas 24h.")
    else:
        df = pd.DataFrame(history)
        df["measured_at"] = pd.to_datetime(df["measured_at"])
        charts = [
            ("temperature_c", "Temperatura (°C)"),
            ("vibration_mm_s", "Vibração (mm/s)"),
            ("current_a", "Corrente (A)"),
            ("voltage_v", "Tensão (V)"),
            ("rpm", "Rotação (rpm)"),
            ("power_kw", "Potência (kW)"),
        ]
        for i in range(0, len(charts), 2):
            left, right = st.columns(2)
            for col_slot, (field, title) in zip((left, right), charts[i:i + 2]):
                with col_slot:
                    fig = px.line(df, x="measured_at", y=field, title=title,
                                  markers=True)
                    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Navegação (sidebar)
# ---------------------------------------------------------------------------
def navigation_sidebar() -> str | None:
    auth = st.session_state["auth"]
    st.sidebar.success(f"👤 {auth['username']} ({auth['role']})")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()
    mode = st.sidebar.radio("Modo", ["🌳 Navegar pela planta", "🔎 Buscar por TAG"])

    selected_tag: str | None = None

    if mode == "🔎 Buscar por TAG":
        query = st.sidebar.text_input("TAG (parcial)", value="").strip()
        if query:
            audit("SEARCH_TAG", query)
            results = repo.search_by_tag(query)
            if results:
                selected_tag = st.sidebar.selectbox(
                    "Resultados", [r["tag"] for r in results]
                )
            else:
                st.sidebar.warning("Nenhuma TAG encontrada.")
    else:
        plants = repo.list_plants()
        if not plants:
            st.sidebar.warning("Nenhuma planta cadastrada. Rode o seed/RPAs.")
            return None
        plant = st.sidebar.selectbox(
            "Planta", plants, format_func=lambda p: f"{p['name']} ({p['code']})"
        )
        areas = repo.list_areas(plant["id"])
        if not areas:
            st.sidebar.info("Planta sem áreas associadas ainda.")
            return None
        area = st.sidebar.selectbox(
            "Área", areas, format_func=lambda a: f"{a['name']} ({a['code']})"
        )
        assets = repo.assets_in_area(area["id"])
        if not assets:
            st.sidebar.info("Área sem ativos associados ainda.")
            return None
        asset = st.sidebar.selectbox(
            "Ativo", assets, format_func=lambda a: f"{a['tag']} — {a['name']}"
        )
        selected_tag = asset["tag"]

    return selected_tag


# ---------------------------------------------------------------------------
# Painel admin: disparo das RPAs + auditoria
# ---------------------------------------------------------------------------
def admin_panel() -> None:
    auth = st.session_state["auth"]
    with st.sidebar.expander("⚙️ Automação (RPA)"):
        if auth["role"] != "admin":
            st.caption("Disponível para o papel admin.")
        else:
            st.caption("Enviar imagem da placa → cadastra o ativo")
            up = st.file_uploader("Imagem da placa", type=["png", "jpg", "jpeg"])
            if up is not None and st.button("📤 Processar placa enviada"):
                from pathlib import Path

                from sprint2.config import settings
                from sprint2.nameplate.bot import NameplateBot

                dest = Path(settings.nameplate_drop_folder)
                dest.mkdir(parents=True, exist_ok=True)
                (dest / up.name).write_bytes(up.getbuffer())
                res = NameplateBot().run()
                audit("RUN_RPA", f"upload:{up.name}")
                if res["ok"]:
                    st.success(f"Placa processada e cadastro atualizado: {res}")
                else:
                    st.error(
                        f"Não foi possível ler a placa enviada: {res}. "
                        "Use uma imagem gerada por gen_nameplates "
                        "(o OCR simulado lê os metadados da placa)."
                    )

            st.divider()
            if st.button("▶ Rodar RPA de placa (pasta de drop)"):
                from sprint2.nameplate.bot import NameplateBot
                res = NameplateBot().run()
                audit("RUN_RPA", "nameplate")
                st.success(f"Placa: {res}")
            if st.button("▶ Rodar RPA de associação"):
                from sprint2.association.bot import AssociationBot
                res = AssociationBot().run()
                audit("RUN_RPA", "association")
                st.success(f"Associação: {res}")


def audit_section() -> None:
    with st.expander("🔍 Auditoria — execuções RPA e acessos"):
        st.caption("Execuções RPA recentes")
        execs = repo.recent_executions(limit=20)
        if execs:
            st.dataframe(pd.DataFrame(execs), hide_index=True,
                         use_container_width=True)
        else:
            st.info("Nenhuma execução registrada.")
        st.caption("Acessos recentes")
        logs = repo.recent_access_logs(limit=20)
        if logs:
            st.dataframe(pd.DataFrame(logs), hide_index=True,
                         use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not st.session_state.get("auth"):
        login_screen()
        return

    st.sidebar.title("🤖 Monitor Operacional")
    if st.sidebar.checkbox("Auto-atualizar (15s)", value=False):
        st.markdown('<meta http-equiv="refresh" content="15">',
                    unsafe_allow_html=True)

    selected_tag = navigation_sidebar()
    admin_panel()

    st.title("Visualização Operacional do Ativo")
    if selected_tag:
        render_asset(selected_tag)
    else:
        st.info("Selecione um ativo pela planta ou busque por TAG na barra lateral.")

    st.divider()
    audit_section()


main()
