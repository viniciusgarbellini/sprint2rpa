"""Sprint 2 — Visualização Operacional e Representação do Ativo.

Pacote dos módulos NOVOS da Sprint 2, que estendem o projeto rpa-cs (Sprint 1):

  - sprint2.nameplate    → RPA de extração da placa do motor → cadastro
  - sprint2.association   → RPA de associação Ativo ↔ TAG ↔ Localização
  - sprint2.app           → interface de navegação/consulta (Streamlit) + login
  - sprint2.repository    → acesso aos dados novos (plants, areas, nameplates…)

Padronizado em Python 3.12 e estrutura de módulos moderna (src-layout,
collections.abc, tipagem `X | None`).
"""

__version__ = "2.0.0"
