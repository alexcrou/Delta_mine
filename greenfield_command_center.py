# greenfield_command_center.py
# Интерактивный модуль для Streamlit-приложения.
# Назначение: запуск greenfield-проектов, дорожная карта, контроль исходных
# данных, матрица проектной документации и экспертиз.
#
# ВАЖНО: нормативная матрица — инструмент управления проектом, а не юридическое
# заключение. Перед утверждением ТЗ/ПД эксперт должен подтвердить применимость
# требований для конкретного объекта, региона и источника финансирования.

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st


# -----------------------------------------------------------------------------
# 1. ДИЗАЙН-СИСТЕМА: «диспетчерская проекта»
# -----------------------------------------------------------------------------

def apply_command_center_theme() -> None:
    """Вызывать один раз сразу после st.set_page_config()."""
    st.markdown("""
    <style>
      :root {
        --ink: #102a43; --muted: #627d98; --paper: #f6f9fc;
        --navy: #082f49; --blue: #0ea5e9; --teal: #14b8a6;
        --amber: #f59e0b; --red: #ef4444; --green: #16a34a;
      }
      .stApp { background: radial-gradient(circle at 90% 0%, #e0f2fe 0, transparent 28%), var(--paper); }
      .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }
      h1, h2, h3 { color: var(--ink); letter-spacing: -.02em; }
      div[data-testid="stMetric"] {
        background: rgba(255,255,255,.92); border: 1px solid #dbe7f0;
        border-radius: 16px; padding: 12px 14px; box-shadow: 0 4px 16px rgba(15, 53, 82, .05);
      }
      div[data-testid="stMetricLabel"] { color: var(--muted); }
      div[data-testid="stMetricValue"] { color: var(--ink); font-weight: 750; }
      .cc-hero { background: linear-gradient(120deg, #082f49, #0c4a6e 58%, #0369a1); color: white;
        border-radius: 22px; padding: 26px 30px; margin: 0 0 20px; box-shadow: 0 15px 35px rgba(8,47,73,.20); }
      .cc-hero h1 { color: white; margin: 0 0 6px; font-size: 2rem; }
      .cc-hero p { margin: 0; color: #dbeafe; }
      .cc-card { background: white; border: 1px solid #dbe7f0; border-radius: 16px; padding: 16px;
        margin: 8px 0; box-shadow: 0 3px 12px rgba(15, 53, 82, .04); }
      .cc-chip { display:inline-block; border-radius: 999px; padding: 4px 10px; margin: 0 6px 6px 0;
        font-size:.78rem; font-weight:650; }
      .chip-ok { background:#dcfce7; color:#166534; }.chip-warn { background:#fef3c7; color:#92400e; }
      .chip-risk { background:#fee2e2; color:#991b1b; }.chip-info { background:#e0f2fe; color:#075985; }
      .cc-next { border-left: 4px solid var(--teal); background: #f0fdfa; border-radius: 0 14px 14px 0;
        padding: 14px 16px; margin: 8px 0; }
      .cc-source { color: #627d98; font-size: .82rem; }
      .stButton > button { border-radius: 10px; font-weight: 650; }
    </style>
    """, unsafe_allow_html=True)


def hero(project_name: str, subtitle: str) -> None:
    st.markdown(
        f'<section class="cc-hero"><h1>⛏ {project_name or "Новый greenfield-проект"}</h1>'
        f'<p>{subtitle}</p></section>', unsafe_allow_html=True
    )


def chip(label: str, kind: str = "info") -> str:
    return f'<span class="cc-chip chip-{kind}">{label}</span>'


# -----------------------------------------------------------------------------
# 2. НОРМАТИВНАЯ/ПРОЕКТНАЯ МАТРИЦА
# -----------------------------------------------------------------------------

BASE_DOCUMENTS = [
    ("Устав проекта", "Управление", "Обязателен внутренним контуром", "Фиксирует цель, границы, команду, сроки, бюджет и риски."),
    ("Календарный план-график / WBS", "Управление", "Обязателен", "Базовый план, логические связи, критический путь, ресурсы."),
    ("Бюджет / план финансирования", "Финансы", "Обязателен", "CAPEX/OPEX, резерв, финансирование по годам и объектам."),
    ("Реестр ИРД", "Исходные данные", "Обязателен", "Владелец, срок, статус, влияние на проектирование/экспертизы."),
    ("Права на землю / земельно-имущественные документы", "ИРД", "Проверить применимость", "Площадки, трассы коммуникаций, отвалы, объекты инфраструктуры."),
    ("Инженерные изыскания", "ИРД", "По составу объекта", "ИГИ, ИГДИ, ИЭИ, ИГМИ; для горных работ — геомеханика и гидрогеология."),
    ("Технические условия", "ИРД", "По необходимости", "Электроснабжение, вода, связь, примыкания, иные внешние подключения."),
]


def requirement_matrix(p: dict) -> list:
    """Возвращает объяснимый список документов/согласований."""
    rows = [{"name": n, "group": g, "need": need, "reason": reason, "confidence": "Проверить экспертом"}
            for n, g, need, reason in BASE_DOCUMENTS]

    def add(name: str, group: str, need: str, reason: str, confidence: str = "По ответам мастера"):
        rows.append({"name": name, "group": group, "need": need, "reason": reason, "confidence": confidence})

    # Недра и ТП
    add("Лицензия на пользование недрами и лицензионные условия", "Недропользование",
        "Критично", "Основание для пользования участком недр; контроль сроков и обязательств.")
    if p.get("reserves_approved"):
        add("Протокол утверждения запасов / кондиций", "Недропользование", "Требуется", "Подтверждает используемую сырьевую базу.")
    else:
        add("ТЭО кондиций, отчет с подсчетом запасов, экспертиза запасов", "Недропользование", "Вероятно требуется",
            "Без подтвержденной сырьевой базы нельзя надежно фиксировать производительность и проектные решения.")
    if p.get("stage") in {"вскрытие", "добыча", "комбинированный"}:
        add("Технический проект разработки месторождения", "Проектирование", "Как правило требуется",
            "Проверить вид пользования недрами, требования лицензии и необходимость рассмотрения в ЦКР-ТПИ.")
        add("Согласование технического проекта в ЦКР-ТПИ Роснедра", "Согласования", "Проверить применимость",
            "Зависит от вида технического проекта и требований к согласованию.")

    # ПД по ПП РФ №87
    if p.get("capital_construction"):
        add("Проектная документация (ПД) по составу ПП РФ №87", "Проектирование", "Требуется",
            "Для объектов капитального строительства: состав разделов определяется объектом, заданием и применимыми требованиями.")
        add("Рабочая документация (РД)", "Проектирование", "Требуется для производства работ",
            "Детализация решений ПД для закупок, СМР, монтажа и исполнительной документации.")
        add("Проект организации строительства (ПОС)", "ПД по №87", "Как правило требуется", "Планирование организации, очередности и безопасности строительства.")
        add("Сметная документация", "ПД / финансы", "Проверить необходимость", "Состав зависит от источника финансирования и решения заказчика.")

    # Экологии, вода, опасность
    if p.get("protected_areas") or p.get("processing") or p.get("tailings"):
        add("ОВОС и государственная экологическая экспертиза (ГЭЭ)", "Экспертизы", "Проверить применимость",
            "Зависит от категории, местоположения, состава объекта и действующих требований к объекту экспертизы.")
    if p.get("capital_construction"):
        add("Государственная / негосударственная экспертиза ПД и результатов изысканий", "Экспертизы", "Определить маршрут",
            "Маршрут определяется видом объекта, финансированием, расположением и законодательными критериями.")
    if p.get("hazardous_facility") or p.get("mine_method") == "подземный":
        add("Идентификация и регистрация ОПО; требования промышленной безопасности", "Промышленная безопасность", "Проверить/требуется",
            "Для опасных производственных объектов и подземных горных работ определить класс опасности и состав обязательств.")
        add("Экспертиза промышленной безопасности (ЭПБ)", "Промышленная безопасность", "По применимости",
            "Не подменять ГГЭ: необходимость зависит от конкретных зданий, сооружений, устройств и документации.")
    if p.get("blasting"):
        add("Проектные решения по БВР, ВМ и площадке/складу ВМ", "Промышленная безопасность", "Требуется", "Определить схему снабжения ВМ и применимые разрешительные требования.")
    if p.get("water_discharge"):
        add("Водохозяйственные решения, водоотлив, очистка и сброс", "Экология/вода", "Требуется", "Шахтные, карьерные и поверхностные воды; проверить водный объект и разрешительные процедуры.")
    if p.get("tailings"):
        add("Проект хвостового хозяйства / ГТС, декларация безопасности, мониторинг", "ГТС", "Требуется", "Хвостохранилище и связанные ГТС требуют отдельной технической и разрешительной проработки.")
    if p.get("infrastructure"):
        add("Отдельные ТЗ и ПД локальных объектов инфраструктуры", "Проектирование", "Рекомендуется", "ВП, РММ, ЛЭП, дороги, котельная, ГСМ, связь — выделять в управляемые пакеты работ.")
    return rows


# -----------------------------------------------------------------------------
# 3. WBS GREENFIELD-ПРОЕКТА
# -----------------------------------------------------------------------------

def make_roadmap(p: dict) -> list:
    start = p.get("target_start") or date.today()
    tasks = [
        ("M0", "Утвердить устав, оргструктуру и базовый план", 15, [], "Инициация", "РП / ОПИК", True),
        ("M1", "Проверить лицензионные условия и реестр обязательств", 10, ["M0"], "Недропользование", "Недропользователь / УЛН", True),
        ("M2", "Подтвердить запасы: ТЭО/подсчет/экспертиза/протокол", 180, ["M1"], "Недропользование", "Геология", True),
        ("M3", "Сформировать и закрыть критичный реестр ИРД", 90, ["M0"], "ИРД", "ОПИК / УВГС", True),
        ("M4", "Выполнить инженерные изыскания, геомеханику и гидрогеологию", 150, ["M3"], "Изыскания", "Генпроектировщик", True),
        ("M5", "ОТР/концепция и выбор стратегии реализации", 45, ["M1", "M3"], "Концепция", "РП / техдиректор", True),
        ("M6", "Разработать и согласовать ТЗ на технический проект", 15, ["M5"], "Проектирование", "РП / ГИП", True),
        ("M7", "Технический проект; внутренняя экспертиза; корректировка", 90, ["M2", "M4", "M6"], "Технический проект", "ГИП", True),
        ("M8", "Согласование технического проекта в ЦКР (при применимости)", 45, ["M7"], "Согласования", "ГИП / УЛН", True),
        ("M9", "Разработать ТЗ на ПД и локальные объекты", 20, ["M5"], "Проектирование", "РП / ГИП", False),
        ("M10", "Разработать ПД по №87 и специальные разделы", 120, ["M4", "M8", "M9"], "ПД", "Генпроектировщик", True),
        ("M11", "Внутренняя экспертиза ПД и устранение замечаний", 25, ["M10"], "ПД", "РП / эксперты", True),
        ("M12", "Внешние экспертизы и согласования (маршрут проекта)", 90, ["M11"], "Экспертизы", "ГИП / УВГС", True),
        ("M13", "Разработать РД и выдать пакеты в производство", 110, ["M10"], "РД", "Генпроектировщик", False),
        ("M14", "Маркетинг, контрактация и long-lead equipment", 120, ["M5"], "Закупки", "МТО", False),
        ("M15", "Подготовка площадки и мобилизация", 45, ["M12", "M13"], "Строительство", "ЗУД по КС", True),
        ("M16", "СМР / ГКР и строительный контроль", 365, ["M15", "M14"], "Строительство", "ЗУД по КС", True),
        ("M17", "ПНР, исполнительная документация, приемка и ввод", 60, ["M16"], "Ввод", "Заказчик / КС", True),
    ]
    if not p.get("capital_construction"):
        tasks = [t for t in tasks if t[0] not in {"M10", "M11", "M12", "M13", "M15", "M16", "M17"}]

    end_by_id = {}
    result = []
    for task_id, work, duration, preds, phase, owner, critical in tasks:
        pred_end = max((end_by_id[x] for x in preds if x in end_by_id), default=start - timedelta(days=1))
        task_start = pred_end + timedelta(days=1)
        task_end = task_start + timedelta(days=duration - 1)
        end_by_id[task_id] = task_end
        result.append({"id": task_id, "work": work, "phase": phase, "owner": owner,
                       "start": task_start, "finish": task_end, "duration": duration,
                       "predecessors": preds, "critical": critical, "status": "Не начато"})
    return result


def roadmap_health(tasks: list, docs: list) -> dict:
    critical_docs = [x for x in docs if x["need"] in {"Критично", "Требуется"}]
    end = max((x["finish"] for x in tasks), default=date.today())
    return {"tasks": len(tasks), "critical": sum(x["critical"] for x in tasks),
            "docs": len(docs), "critical_docs": len(critical_docs), "forecast_end": end}


# -----------------------------------------------------------------------------
# 4. ИНТЕРАКТИВНЫЙ МАСТЕР
# -----------------------------------------------------------------------------

def greenfield_intake() -> dict:
    st.subheader("🧭 Диагностика greenfield-проекта")
    st.caption("Займет 5-7 минут. Можно выбирать «неизвестно»: система создаст задачу на уточнение.")
    with st.form("greenfield_intake", border=False):
        a, b = st.columns(2)
        with a:
            project_name = st.text_input("Название проекта / месторождения *")
            company = st.text_input("Заказчик / недропользователь *")
            region = st.text_input("Регион и район размещения")
            mine_method = st.radio("Способ разработки", ["подземный", "открытый", "комбинированный", "неизвестно"], horizontal=True)
            stage = st.selectbox("Предмет текущего этапа", ["вскрытие", "добыча", "разведка", "инфраструктура", "комбинированный"])
            target_start = st.date_input("Целевая дата старта проекта", value=date.today())
        with b:
            has_license = st.radio("Лицензия на недра", ["есть", "нет", "неизвестно"], horizontal=True)
            reserves = st.radio("Запасы утверждены?", ["да", "нет", "в процессе", "неизвестно"], horizontal=True)
            capital = st.radio("Есть объекты капитального строительства?", ["да", "нет", "неизвестно"], horizontal=True)
            infra = st.checkbox("Включены инфраструктурные объекты: ВП, РММ, ЛЭП, дороги, ГСМ")
            processing = st.checkbox("Включены фабрика / переработка")
            tailings = st.checkbox("Есть хвостовое хозяйство / ГТС")
            blasting = st.checkbox("Предусмотрены БВР и ВМ")
            water = st.checkbox("Есть водоотлив, очистка или сброс вод")
            protected = st.checkbox("Есть ООПТ, водные объекты или иные чувствительные ограничения")
            hazardous = st.checkbox("Объект относится / может относиться к ОПО")
        submitted = st.form_submit_button("Построить первичную дорожную карту", type="primary", use_container_width=True)
    if not submitted:
        return {}
    return {
        "project_name": project_name or "Greenfield-проект", "company": company, "region": region,
        "mine_method": mine_method, "stage": stage, "target_start": target_start,
        "has_license": has_license == "есть", "reserves_approved": reserves == "да",
        "capital_construction": capital == "да", "infrastructure": infra, "processing": processing,
        "tailings": tailings, "blasting": blasting, "water_discharge": water,
        "protected_areas": protected, "hazardous_facility": hazardous,
    }


# -----------------------------------------------------------------------------
# 5. ЭКРАН РУКОВОДИТЕЛЯ
# -----------------------------------------------------------------------------

def render_dashboard(project: dict, tasks: list, docs: list) -> None:
    health = roadmap_health(tasks, docs)
    hero(project.get("project_name", "Greenfield-проект"),
         f"{project.get('company') or 'Заказчик не указан'} · {project.get('region') or 'Регион не указан'}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Работ в дорожной карте", health["tasks"])
    c2.metric("Критических работ", health["critical"])
    c3.metric("Требований к документам", health["docs"])
    c4.metric("Прогноз завершения", health["forecast_end"].strftime("%d.%m.%Y"))

    blockers = []
    if not project.get("has_license"): blockers.append("Подтвердить лицензию и ее условия")
    if not project.get("reserves_approved"): blockers.append("Подтвердить запасы / маршрут их утверждения")
    if project.get("capital_construction") and not project.get("infrastructure"):
        blockers.append("Проверить достаточность инфраструктуры до начала основных работ")
    if project.get("mine_method") == "подземный" and not project.get("water_discharge"):
        blockers.append("Подтвердить решения по водоотливу и водоотведению")

    st.subheader("Следующие действия")
    if blockers:
        for item in blockers:
            st.markdown(f'<div class="cc-next"><b>Приоритет:</b> {item}<br><span class="cc-source">Создано по ответам мастера; требуется назначить владельца и срок.</span></div>', unsafe_allow_html=True)
    else:
        st.success("Первичные блокирующие условия не выявлены. Перейдите к настройке ИРД, ТЗ и дат дорожной карты.")

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Критический маршрут")
        for x in [t for t in tasks if t["critical"]][:8]:
            st.markdown(f"**{x['id']} · {x['work']}**  ")
            st.caption(f"{x['start']:%d.%m.%Y} — {x['finish']:%d.%m.%Y} · {x['owner']}")
    with right:
        st.subheader("Профиль проекта")
        labels = [
            chip(f"{project.get('mine_method', '—')} способ", "info"),
            chip(f"этап: {project.get('stage', '—')}", "info"),
            chip("ОПО: проверить", "warn" if project.get("hazardous_facility") else "info"),
            chip("БВР", "warn") if project.get("blasting") else "",
            chip("ГТС/ХХ", "risk") if project.get("tailings") else "",
        ]
        st.markdown("".join(labels), unsafe_allow_html=True)
        st.info("Совет: утвердите владельцев критических ИРД до выпуска ТЗ. Иначе график будет выглядеть реалистично, но не будет исполнимым.")


def render_requirements(docs: list) -> None:
    st.subheader("📚 Матрица документации и экспертиз")
    groups = sorted({x["group"] for x in docs})
    selected = st.multiselect("Фильтр по блоку", groups, default=groups)
    for row in [x for x in docs if x["group"] in selected]:
        kind = "risk" if row["need"] == "Критично" else "warn" if row["need"] in {"Требуется", "Как правило требуется"} else "info"
        with st.expander(f"{row['group']} · {row['name']} · {row['need']}"):
            st.markdown(chip(row["need"], kind) + chip(row["confidence"], "info"), unsafe_allow_html=True)
            st.write(row["reason"])
            st.caption("Решение о применимости фиксируется ответственным экспертом в карточке требования.")


def render_roadmap(tasks: list) -> None:
    st.subheader("🗺 Дорожная карта")
    phases = list(dict.fromkeys(x["phase"] for x in tasks))
    selected = st.multiselect("Фазы", phases, default=phases)
    for phase in selected:
        phase_tasks = [x for x in tasks if x["phase"] == phase]
        with st.expander(f"{phase} · {len(phase_tasks)} работ", expanded=phase in {"Инициация", "Недропользование", "ИРД"}):
            for task in phase_tasks:
                marker = "🔴" if task["critical"] else "🔵"
                st.markdown(f"{marker} **{task['id']} — {task['work']}**")
                st.caption(f"{task['start']:%d.%m.%Y} → {task['finish']:%d.%m.%Y} · {task['duration']} дн. · {task['owner']} · предшественники: {', '.join(task['predecessors']) or 'нет'}")


# -----------------------------------------------------------------------------
# 6. ТОЧКА ВХОДА В app.py
# -----------------------------------------------------------------------------

def greenfield_page(state) -> None:
    """state — st.session_state."""
    if "gf_project" not in state: state["gf_project"] = {}
    if "gf_tasks" not in state: state["gf_tasks"] = []
    if "gf_requirements" not in state: state["gf_requirements"] = []

    if not state["gf_project"]:
        hero("Greenfield command center", "От лицензии и запасов до ввода объекта в эксплуатацию")
        data = greenfield_intake()
        if data:
            state["gf_project"] = data
            state["gf_tasks"] = make_roadmap(data)
            state["gf_requirements"] = requirement_matrix(data)
            st.rerun()
        return

    page = st.radio("Раздел", ["Рабочий стол", "Дорожная карта", "Документация и экспертизы", "Перепройти диагностику"], horizontal=True)
    if page == "Рабочий стол":
        render_dashboard(state["gf_project"], state["gf_tasks"], state["gf_requirements"])
    elif page == "Дорожная карта":
        render_roadmap(state["gf_tasks"])
    elif page == "Документация и экспертизы":
        render_requirements(state["gf_requirements"])
    else:
        state["gf_project"] = {}
        state["gf_tasks"] = []
        state["gf_requirements"] = []
        st.rerun()
