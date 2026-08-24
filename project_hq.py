# project_hq.py
# Цифровой штаб руководителя проекта — агрегатор всех модулей «Горного Дельта».
# Синхронизация: greenfield_command_center (профиль+дорожная карта),
# ai_project_copilot (факты), база знаний app.py (S.docs), wizard (S.project).
# Python 3.9+ / Streamlit Cloud compatible.

from __future__ import annotations

import re
from datetime import date
from typing import Dict, List, Optional

import streamlit as st

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False


PROJECT_TYPES = [
    "Горнодобывающий проект", "Подземный рудник", "Карьер", "Обогатительная фабрика",
    "Инфраструктура", "Энергетика / ЛЭП", "Вахтовый посёлок", "Комплексный инвестиционный проект",
]

TZ_TYPES = [
    "Технический проект разработки месторождения",
    "Проектная документация: вскрытие / горно-капитальные работы",
    "Проектная документация: инфраструктура",
    "Проектная документация: электроснабжение / ЛЭП",
    "Проектная документация: вахтовый посёлок",
    "Индивидуальное техническое задание",
]

STAGES = [
    ("G0", "Инициация", "Цели, заказчик, основание, границы проекта"),
    ("G1", "Концепция", "ОТР/концепция, варианты, ключевые допущения"),
    ("G2", "Исходные данные", "ИРД, лицензии, права на землю, изыскания"),
    ("G3", "Проектирование", "ТП/ПД/РД, внутренние экспертизы"),
    ("G4", "Разрешения и экспертизы", "ЦКР, ГГЭ, ГЭЭ, НГЭ, РНС — по применимости"),
    ("G5", "Закупки и строительство", "Контрактация, поставки, СМР, ПНР"),
    ("G6", "Ввод и закрытие", "Ввод, отнесение затрат, закрывающие документы"),
]

DEFAULT_ROADMAP = [
    ["G0", "Открытие проекта / приказ", "Инициация", "", "", 0, "Основание для запуска"],
    ["G1", "Утверждение концепции и ОТР", "Концепция", "", "", 0, "Решение по варианту реализации"],
    ["G2", "Сбор ИРД и инженерные изыскания", "Исходные данные", "", "", 0, "Комплектность ИРД подтверждена"],
    ["G3", "Разработка ТП / ПД / РД", "Проектирование", "", "", 0, "Документация передана на проверку"],
    ["G4", "Экспертизы, согласования, разрешения", "Разрешения", "", "", 0, "Положительные заключения / РНС"],
    ["G5", "Контрактация, поставка, СМР и ПНР", "Реализация", "", "", 0, "Готовность к вводу"],
    ["G6", "Ввод в эксплуатацию и закрытие", "Ввод", "", "", 0, "Акт ввода / акт закрытия"],
]

HQ_FACT_DEFAULTS = {}


def init_hq_state(state) -> None:
    if PANDAS_OK:
        roadmap_df = pd.DataFrame(DEFAULT_ROADMAP, columns=["Gate", "Работа", "Контур", "Начало", "Окончание", "%", "Критерий готовности"])
        budget_df = pd.DataFrame(columns=["Статья", "Тип затрат", "2026", "2027", "2028", "2029", "2030", "Итого"])
        risks_df = pd.DataFrame(columns=["Риск", "Вероятность", "Влияние", "Владелец", "Мероприятие"])
        team_df = pd.DataFrame(columns=["ФИО", "Подразделение", "Должность", "Роль", "Функции"])
    else:
        roadmap_df = budget_df = risks_df = team_df = None
    defaults = {"hq_facts": {}, "hq_roadmap": roadmap_df, "hq_budget": budget_df,
                "hq_risks": risks_df, "hq_team": team_df}
    for key, value in defaults.items():
        if key not in state and value is not None:
            state[key] = value


def txt(value: Optional[str], empty: str = "Требует заполнения") -> str:
    value = (value or "").strip()
    return value if value else empty


def find_value(text: str, patterns: List[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .;:")
    return ""


def extract_facts(text: str) -> Dict[str, str]:
    return {
        "project_name": find_value(text, [r"(?:УСТАВ\s+ИНВЕСТИЦИОННОГО\s+ПРОЕКТА|проект[ау]?|ИП)\s*[«\"]([^»\"\n]{3,120})"]),
        "customer": find_value(text, [r"(?:Заказчик проекта|Заказчик)\s*[:\n]?\s*([^\n]{3,160})"]),
        "location": find_value(text, [r"(?:местоположение проектируемого объекта|местоположение)\s*[:\n]?\s*([^\n]{8,250})"]),
        "license": find_value(text, [r"(Лицензи[яи][^\n]{0,180})"]),
        "basis": find_value(text, [r"(?:Основание для открытия проекта|Основание для проектирования)\s*[-:]?\s*([^\n]{5,300})"]),
    }


# ---------------- СИНХРОНИЗАЦИЯ С ДРУГИМИ МОДУЛЯМИ ----------------

def sync_from_greenfield(state) -> List[str]:
    """Тянет профиль проекта и дорожную карту из greenfield_command_center."""
    notes = []
    gf = state.get("gf_project", {}) if hasattr(state, "get") else (state.gf_project if "gf_project" in state else {})
    if not gf:
        return notes
    f = state.hq_facts
    mapping = {
        "project_name": gf.get("project_name", ""),
        "customer": gf.get("company", ""),
        "location": gf.get("region", ""),
    }
    for key, value in mapping.items():
        if value and not f.get(key):
            f[key] = value
            notes.append(f"Greenfield: «{key}» = {value}")
    method = gf.get("mine_method", "")
    if method and not f.get("description"):
        f["description"] = f"Способ разработки: {method}; этап: {gf.get('stage', '—')}."
        notes.append("Greenfield: заполнено описание (способ разработки).")
    # Дорожная карта
    gf_tasks = state.gf_tasks if "gf_tasks" in state else []
    if gf_tasks and PANDAS_OK and "hq_roadmap" in state:
        existing = set(state.hq_roadmap["Работа"].astype(str))
        rows = []
        for t in gf_tasks:
            if str(t["work"]) not in existing:
                rows.append(["G2", t["work"], t.get("phase", ""), str(t.get("start", "")),
                             str(t.get("finish", "")), 0, f"Владелец: {t.get('owner', '—')}"])
        if rows:
            state.hq_roadmap = pd.concat([state.hq_roadmap, pd.DataFrame(rows, columns=state.hq_roadmap.columns)], ignore_index=True)
            notes.append(f"Greenfield: добавлено работ в дорожную карту: {len(rows)}")
    return notes


def sync_from_copilot(state) -> List[str]:
    """Тянет факты из AI Project Copilot (только подтверждённые пользователем)."""
    notes = []
    facts = state.copilot_facts if "copilot_facts" in state else {}
    f = state.hq_facts
    key_map = {"license": "license", "project_goal": "goal", "budget": "kpi"}
    for ck, item in facts.items():
        if isinstance(item, dict) and item.get("confidence") == "Подтверждено":
            target = key_map.get(ck)
            if target and not f.get(target):
                f[target] = item.get("value", "")
                notes.append(f"Copilot (подтверждено): «{target}» из чата")
    return notes


def sync_from_wizard(state) -> List[str]:
    """Тянет параметры мастера «Новый проект» из app.py."""
    notes = []
    p = state.project if "project" in state else None
    if not p:
        return notes
    f = state.hq_facts
    if p.get("name") and not f.get("project_name"):
        f["project_name"] = p["name"]
        notes.append("Мастер проекта: название")
    if not f.get("description"):
        method = ("подземный" if p.get("underground") else "") + (" открытый" if p.get("open_pit") else "")
        if method.strip():
            f["description"] = f"Способ разработки: {method.strip()}; объём добычи {p.get('volume', 0):,} т/год.".replace(",", " ")
            notes.append("Мастер проекта: описание (способ/объём)")
    return notes


def sync_all(state) -> List[str]:
    notes = []
    notes += sync_from_greenfield(state)
    notes += sync_from_copilot(state)
    notes += sync_from_wizard(state)
    return notes


def knowledge_evidence(state, query: str, top_n: int = 2) -> List[str]:
    """Фрагменты из базы знаний app.py (S.docs) как доказательная база."""
    docs = state.docs if "docs" in state else []
    if not docs:
        return []
    q_words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 3]
    if not q_words:
        return []
    scored = []
    for d in docs:
        text = d.get("text", "")
        chunks = [text[i:i + 600] for i in range(0, min(len(text), 60000), 500)]
        best, best_score = "", 0
        for ch in chunks:
            score = sum(1 for w in q_words if w in ch.lower())
            if score > best_score:
                best, best_score = ch, score
        if best_score > 0:
            scored.append((best_score, d["name"], best))
    scored.sort(key=lambda x: -x[0])
    return [f"{n}: {c[:400]}" for _, n, c in scored[:top_n]]


# ---------------- ГЕНЕРАТОРЫ ДОКУМЕНТОВ ----------------

def generate_charter_markdown(f: Dict[str, str], state) -> str:
    rows_roadmap = []
    if PANDAS_OK and "hq_roadmap" in state and not state.hq_roadmap.empty:
        for _, r in state.hq_roadmap.iterrows():
            rows_roadmap.append("| {0} | {1} | {2} | {3} |".format(
                r["Работа"], txt(str(r["Начало"]), "—"), txt(str(r["Окончание"]), "—"), r.get("Критерий готовности", "")))
    budget_rows = ["| Требует заполнения | — | — | — | — | — | — | — |"]
    if PANDAS_OK and "hq_budget" in state and not state.hq_budget.empty:
        budget_rows = ["| " + " | ".join(str(r.get(c, "")) for c in state.hq_budget.columns) + " |"
                       for _, r in state.hq_budget.iterrows()]
    risk_rows = ["| Требует заполнения | — | — | — | — |"]
    if PANDAS_OK and "hq_risks" in state and not state.hq_risks.empty:
        risk_rows = ["| " + " | ".join(str(r.get(c, "")) for c in state.hq_risks.columns) + " |"
                     for _, r in state.hq_risks.iterrows()]
    team_rows = ["| Требует заполнения | — | — | — | — |"]
    if PANDAS_OK and "hq_team" in state and not state.hq_team.empty:
        team_rows = ["| " + " | ".join(str(r.get(c, "")) for c in state.hq_team.columns) + " |"
                     for _, r in state.hq_team.iterrows()]

    return f"""# УСТАВ ИНВЕСТИЦИОННОГО ПРОЕКТА
## «{txt(f.get('project_name'))}»

**Руководитель проекта:** {txt(f.get('project_manager'))}  
**Заказчик:** {txt(f.get('customer'))}  
**Версия:** черновик, сформирован в Цифровом штабе. Все поля проверяются ответственными лицами.

## 1. Основание
- Основание для открытия: {txt(f.get('basis'))}
- Целевая дата завершения: {txt(f.get('close_date'))}

## 2. Описание и границы
**Тип проекта:** {txt(f.get('project_type'))}  
**Местоположение:** {txt(f.get('location'))}  
**Права / лицензия:** {txt(f.get('license'))}  
**Границы:** {txt(f.get('description'))}

## 3. Цель и результаты
**Цель:** {txt(f.get('goal'))}  
**Результаты:** {txt(f.get('results'))}  
**Показатели:** {txt(f.get('kpi'))}

## 4. Проектная группа
| ФИО | Подразделение | Должность | Роль | Функции |
|---|---|---|---|---|
{chr(10).join(team_rows)}

## 5. Этапы реализации
| Работа | Начало | Окончание | Критерий |
|---|---|---|---|
{chr(10).join(rows_roadmap)}

## 6. Бюджет
Источник финансирования: {txt(f.get('funding_source'))}

| Статья | Тип затрат | Годы | Итого |
|---|---|---|---|
{chr(10).join(budget_rows)}

## 7. Риски
| Риск | Вероятность | Влияние | Владелец | Мероприятие |
|---|---|---|---|---|
{chr(10).join(risk_rows)}

## 8. Взаимосвязь с другими проектами
{txt(f.get('dependencies'))}

> Автогенерация не заменяет экспертизу и согласование в СЭД. Источники данных: мастер проекта, Greenfield command center, AI Copilot, загруженные документы.
"""


def generate_tz_markdown(f: Dict[str, str]) -> str:
    tz_type = f.get("tz_type", TZ_TYPES[0])
    return f"""# ЗАДАНИЕ НА ПРОЕКТНЫЕ РАБОТЫ
## «{txt(f.get('tz_title'))}»

**Тип задания:** {tz_type}  
**Заказчик:** {txt(f.get('customer'))}  
**Проектировщик:** {txt(f.get('designer'))}  
**Дата версии:** {date.today().strftime('%d.%m.%Y')}

| № | Данные и требования | Содержание |
|---:|---|---|
| 1 | Объект и местоположение | {txt(f.get('tz_title'))}; {txt(f.get('location'))} |
| 2 | Основание для проектирования | {txt(f.get('basis'))} |
| 3 | Заказчик, права на недра/землю | {txt(f.get('customer'))}; {txt(f.get('license'))} |
| 4 | Источник финансирования | {txt(f.get('funding_source'))} |
| 5 | Основные ТЭП | {txt(f.get('technical_economic_indicators'))} |
| 6 | Технологические решения | {txt(f.get('technical_solutions'))} |
| 7 | Инфраструктура и обеспечение | {txt(f.get('engineering'))} |
| 8 | Этапы строительства | {txt(f.get('construction_stages'))} |
| 9 | Состав документации | Определяется применимыми нормативными требованиями и решением заказчика |
| 10 | Исходные данные | {txt(f.get('source_data'))} |
| 11 | Экспертизы и согласования | {txt(f.get('expertise_support'))} |

## Контроль комплектности ИРД
- [ ] Лицензия на недра (если применимо)
- [ ] Документы на земельные участки
- [ ] Результаты инженерных изысканий
- [ ] Утверждённые запасы / кондиции
- [ ] Границы проектирования и ТЭП

> Проектировщик и заказчик подтверждают полноту ИРД до выдачи задания в работу.
"""


# ---------------- ГЛАВНЫЙ ЭКРАН ----------------

def project_hq_page(state) -> None:
    init_hq_state(state)
    st.header("🏗️ Цифровой штаб руководителя проекта")
    st.caption("Единый центр: паспорт проекта, дорожная карта, бюджет, риски, Устав и ТЗ. "
               "Данные синхронизируются со всеми модулями платформы.")

    if st.button("🔄 Синхронизировать со всеми модулями", type="primary"):
        notes = sync_all(state)
        if notes:
            for n in notes:
                st.markdown("• " + n)
            st.success("Синхронизация выполнена.")
        else:
            st.info("Новых данных из модулей не найдено. Заполните Greenfield-диагностику, мастер проекта или загрузите документы.")
        st.divider()

    f = state.hq_facts

    page = st.radio("Раздел", ["1. Паспорт проекта", "2. Дорожная карта", "3. Бюджет и риски",
                                "4. Конструктор Устава", "5. Конструктор ТЗ"], horizontal=True)

    if page.startswith("1"):
        st.subheader("Стартовый паспорт")
        c1, c2 = st.columns(2)
        f["project_name"] = c1.text_input("Наименование проекта", f.get("project_name", ""))
        f["project_type"] = c2.selectbox("Тип проекта", PROJECT_TYPES,
                                          index=PROJECT_TYPES.index(f.get("project_type")) if f.get("project_type") in PROJECT_TYPES else 0)
        f["customer"] = c1.text_input("Заказчик", f.get("customer", ""))
        f["project_manager"] = c2.text_input("Руководитель проекта", f.get("project_manager", ""))
        f["location"] = st.text_input("Местоположение", f.get("location", ""))
        f["basis"] = st.text_area("Основание для запуска", f.get("basis", ""), height=68)
        f["license"] = st.text_input("Лицензия на недра / права", f.get("license", ""))
        f["goal"] = st.text_area("Измеримая цель", f.get("goal", ""), height=68)
        f["results"] = st.text_area("Результаты к закрытию", f.get("results", ""), height=68)
        f["close_date"] = st.text_input("Целевая дата завершения", f.get("close_date", ""))
        f["funding_source"] = st.text_input("Источник финансирования", f.get("funding_source", "Собственные средства"))
        f["description"] = st.text_area("Границы проекта", f.get("description", ""), height=90)
        f["dependencies"] = st.text_area("Связанные проекты", f.get("dependencies", ""), height=68)

        # Автоизвлечение фактов из базы знаний
        st.divider()
        st.subheader("Доказательная база (база знаний)")
        if "docs" in state and state.docs:
            st.caption(f"Документов в базе знаний: {len(state.docs)}")
            query = st.text_input("Поиск по базе знаний для проверки факта", placeholder="например: лицензия, заказчик, запасы")
            if query:
                for frag in knowledge_evidence(state, query):
                    st.info(frag)
        else:
            st.info("База знаний пуста — загрузите документы в разделе «📂 Документы проекта».")

    elif page.startswith("2"):
        st.subheader("Дорожная карта и stage-gate контроль")
        if not PANDAS_OK:
            st.error("Нужна библиотека pandas: pip install pandas")
            return
        state.hq_roadmap = st.data_editor(state.hq_roadmap, num_rows="dynamic",
                                           use_container_width=True, key="hq_roadmap_editor")
        roadmap = state.hq_roadmap.copy()
        if not roadmap.empty:
            roadmap["_pct"] = __import__("pandas").to_numeric(roadmap["%"], errors="coerce").fillna(0)
            cols = st.columns(7)
            for i, (gate, name, evidence) in enumerate(STAGES):
                items = roadmap[roadmap["Gate"].astype(str) == gate]
                avg = int(items["_pct"].mean()) if not items.empty else 0
                cols[i].metric(gate, f"{avg}%", name)
                cols[i].caption(evidence)

    elif page.startswith("3"):
        st.subheader("Бюджет и риски")
        if not PANDAS_OK:
            st.error("Нужна библиотека pandas: pip install pandas")
            return
        left, right = st.columns(2)
        with left:
            st.caption("Бюджет по статьям и годам (тыс. руб.)")
            state.hq_budget = st.data_editor(state.hq_budget, num_rows="dynamic",
                                              use_container_width=True, key="hq_budget_editor")
            if not state.hq_budget.empty:
                numeric = [c for c in state.hq_budget.columns if c not in ("Статья", "Тип затрат", "Итого")]
                for col in numeric:
                    state.hq_budget[col] = pd.to_numeric(state.hq_budget[col], errors="coerce").fillna(0)
                state.hq_budget["Итого"] = state.hq_budget[numeric].sum(axis=1)
                st.metric("ИТОГО, тыс. руб.", f"{state.hq_budget['Итого'].sum():,.1f}".replace(",", " "))
        with right:
            st.caption("Реестр рисков")
            state.hq_risks = st.data_editor(
                state.hq_risks, num_rows="dynamic", use_container_width=True,
                column_config={
                    "Вероятность": st.column_config.SelectboxColumn(options=["Низкая", "Средняя", "Высокая"]),
                    "Влияние": st.column_config.SelectboxColumn(options=["Низкое", "Среднее", "Высокое", "Критическое"]),
                }, key="hq_risk_editor")

    elif page.startswith("4"):
        st.subheader("Конструктор Устава")
        f["kpi"] = st.text_input("Показатели эффективности", f.get("kpi", ""))
        charter = generate_charter_markdown(f, state)
        st.divider()
        st.markdown(charter)
        st.download_button("Скачать Устав (.md)", charter, file_name="ustav_proekta_draft.md", mime="text/markdown")

    else:
        st.subheader("Конструктор ТЗ")
        f["tz_type"] = st.selectbox("Тип ТЗ", TZ_TYPES,
                                     index=TZ_TYPES.index(f.get("tz_type")) if f.get("tz_type") in TZ_TYPES else 0)
        f["tz_title"] = st.text_input("Наименование объекта / ТЗ", f.get("tz_title", f.get("project_name", "")))
        f["designer"] = st.text_input("Генпроектировщик", f.get("designer", ""))
        f["technical_economic_indicators"] = st.text_area("Основные ТЭП", f.get("technical_economic_indicators", ""), height=70)
        f["technical_solutions"] = st.text_area("Технологические решения", f.get("technical_solutions", ""), height=110)
        f["engineering"] = st.text_area("Инженерное обеспечение", f.get("engineering", ""), height=70)
        f["construction_stages"] = st.text_area("Этапы строительства", f.get("construction_stages", ""), height=70)
        f["source_data"] = st.text_area("Исходные данные", f.get("source_data", ""), height=70)
        f["expertise_support"] = st.text_area("Экспертизы и согласования", f.get("expertise_support", ""), height=70)
        tz = generate_tz_markdown(f)
        st.divider()
        st.markdown(tz)
        st.download_button("Скачать ТЗ (.md)", tz, file_name="tz_draft.md", mime="text/markdown")
