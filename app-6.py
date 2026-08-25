# ============================================================
#  ГОРНЫЙ ДЕЛЬТА v2.1 — ИИ-платформа руководителя проектов
#  (горнодобывающие предприятия: открытые и подземные работы)
#  Единый файл: включает Greenfield Command Center
# ============================================================
#  ЗАПУСК ЛОКАЛЬНО:  pip install streamlit pandas pypdf python-docx openpyxl
#                    streamlit run app.py
#  ЗАПУСК В ОБЛАКЕ:  Streamlit Cloud
# ============================================================

import streamlit as st
import pandas as pd
import json
import os
import datetime
import re
from datetime import date, timedelta

# ---------- НАСТРОЙКИ ВЛАДЕЛЬЦА ----------
OWNER_PASSWORD = "CHANGE_ME_2026"
PRICE_BASIC = 4900
PRICE_PRO = 14900
PROMO_CODES = {"PILOT2026": "pro", "DEMO": "basic"}
LOG_FILE = "users_log.jsonl"
DOCS_DIR = "knowledge"
os.makedirs(DOCS_DIR, exist_ok=True)
# ---------------------------------------------------------------

st.set_page_config(page_title="Горный Дельта — ИИ-платформа РП", page_icon="⛏", layout="wide")

# ============================================================
#  ТЁМНАЯ ТЕМА (всегда)
# ============================================================
st.markdown("""
<style>
  .stApp { background: #0b1220; color: #e2e8f0; }
  .stApp, .stApp p, .stApp span, .stApp li, .stApp label { color: #cbd5e1; }
  h1, h2, h3, h4 { color: #f1f5f9 !important; letter-spacing: -.02em; }
  section[data-testid="stSidebar"] { background: #0f172a; border-right: 1px solid #1e293b; }
  section[data-testid="stSidebar"] * { color: #cbd5e1; }
  .stTextInput > div > div > input, .stTextArea textarea,
  .stNumberInput input, .stDateInput input {
    background: #111c33 !important; color: #e2e8f0 !important;
    border: 1px solid #27364f !important; border-radius: 10px;
  }
  .stButton > button {
    background: #155e75 !important; color: #e0f2fe !important;
    border: 1px solid #0e7490 !important; border-radius: 10px; font-weight: 650;
  }
  .stButton > button:hover { background: #0e7490 !important; }
  div[data-testid="stMetric"] {
    background: #111c33; border: 1px solid #27364f; border-radius: 14px;
    padding: 12px 14px; box-shadow: 0 4px 16px rgba(0,0,0,.35);
  }
  div[data-testid="stMetricLabel"] { color: #7c93b3; }
  div[data-testid="stMetricValue"] { color: #7dd3fc; font-weight: 750; }
  div[data-testid="stExpander"] {
    background: #101a2e; border: 1px solid #27364f; border-radius: 12px;
  }
  div[data-testid="stForm"] { background: #101a2e; border: 1px solid #27364f; border-radius: 14px; }
  .stRadio label, .stCheckbox label { color: #cbd5e1; }
  div[data-testid="stFileUploaderDropzone"] {
    background: #111c33; border: 1px dashed #27364f; color: #7c93b3;
  }
  .cc-hero { background: linear-gradient(120deg, #082f49, #0c4a6e 58%, #0369a1); color: #fff;
    border-radius: 18px; padding: 22px 26px; margin: 0 0 18px; box-shadow: 0 12px 30px rgba(0,0,0,.45); }
  .cc-hero h1 { color: #fff !important; margin: 0 0 6px; font-size: 1.7rem; }
  .cc-hero p { margin: 0; color: #bae6fd; }
  .cc-chip { display:inline-block; border-radius:999px; padding:3px 10px; margin:0 6px 6px 0;
    font-size:.78rem; font-weight:650; }
  .chip-ok { background:#14532d; color:#bbf7d0; } .chip-warn { background:#78350f; color:#fde68a; }
  .chip-risk { background:#7f1d1d; color:#fecaca; } .chip-info { background:#0c4a6e; color:#bae6fd; }
  .cc-next { border-left: 4px solid #14b8a6; background: #0f2e2b; border-radius: 0 12px 12px 0;
    padding: 12px 14px; margin: 8px 0; color:#d1fae5; }
  .cc-source { color:#5e7d92; font-size:.82rem; }
</style>
""", unsafe_allow_html=True)

# ---------- СОСТОЯНИЕ ----------
S = st.session_state
defaults = {
    "plan": "free", "show_owner": False, "wizard_done": False,
    "project": None, "docs": [], "messages": [],
    "gf_project": {}, "gf_tasks": [], "gf_requirements": [], "roadmap": None,
}
for k, v in defaults.items():
    if k not in S:
        S[k] = v

# ---------- ЖУРНАЛ ----------
def log_request(user_id, mode, text, meta=""):
    entry = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "user": user_id, "mode": mode, "text": text, "meta": meta}
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def read_log():
    if not os.path.exists(LOG_FILE):
        return []
    out = []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return out

# ---------- ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ ----------
def psych_profile(entries):
    if not entries:
        return "Данных пока нет."
    texts = [e["text"].lower() for e in entries]
    joined = " ".join(texts)
    n = len(entries)
    traits = []
    if sum(t.count("?") for t in texts) / max(n, 1) >= 1.5:
        traits.append("Задаёт много уточняющих вопросов — аккуратный, проверяющий тип руководителя.")
    if any(w in joined for w in ["срочно", "быстрее", "дедлайн", "срок"]):
        traits.append("Озабочен сроками — работает под давлением дедлайнов, вероятно перегружен.")
    if any(w in joined for w in ["смета", "бюджет", "стоимость", "экономия", "уменьшить"]):
        traits.append("Фокус на деньгах — прагматик, ищет оптимизацию затрат.")
    if any(w in joined for w in ["норм", "снип", "фнп", "ростехнадзор", "экспертиз", "лиценз"]):
        traits.append("Осторожен в нормативной части — вероятно, недавно сталкивался с проверками.")
    if any(w in joined for w in ["письмо", "протокол", "повестк", "устав"]):
        traits.append("Делегирует рутину — бережёт время для управления.")
    avg_len = sum(len(t) for t in texts) / max(n, 1)
    if avg_len < 80:
        traits.append("Кратко формулирует — решительный стиль, хочет ответ «по делу».")
    else:
        traits.append("Подробно описывает задачи — вдумчивый, любит контекст.")
    if not traits:
        traits.append("Мало данных — наблюдение продолжается.")
    return "\n".join(f"• {t}" for t in traits)

# ---------- ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ ФАЙЛОВ ----------
def extract_text(file) -> str:
    name = file.name.lower()
    try:
        if name.endswith((".txt", ".md", ".csv", ".json")):
            return file.getvalue().decode("utf-8", errors="ignore")
        if name.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                import io
                reader = PdfReader(io.BytesIO(file.getvalue()))
                return "\n".join((p.extract_text() or "") for p in reader.pages[:30])
            except ImportError:
                return "[PDF-библиотека не установлена: pip install pypdf]"
        if name.endswith(".docx"):
            try:
                import docx
                import io
                d = docx.Document(io.BytesIO(file.getvalue()))
                return "\n".join(p.text for p in d.paragraphs if p.text.strip())
            except ImportError:
                return "[python-docx не установлена: pip install python-docx]"
        if name.endswith((".xlsx", ".xls")):
            try:
                import openpyxl
                import io
                wb = openpyxl.load_workbook(io.BytesIO(file.getvalue()))
                out = []
                for ws in wb.worksheets[:10]:
                    for row in ws.iter_rows(max_row=100):
                        vals = [str(c.value) for c in row if c.value is not None]
                        if vals:
                            out.append(" | ".join(vals))
                return "\n".join(out)
            except ImportError:
                return "[openpyxl не установлена: pip install openpyxl]"
        if name.endswith(".dwg"):
            raw = file.getvalue()
            try:
                text = raw.decode("utf-16-le", errors="ignore")
            except Exception:
                text = ""
            words = re.findall(r"[А-Яа-яA-Za-z0-9 .,\-()№]{6,}", text)
            return "\n".join(words[:200]) if words else "[DWG: текстовые данные не извлечены]"
    except Exception as e:
        return f"[Ошибка чтения файла: {e}]"
    return "[Формат не поддерживается]"

# ---------- КЛАССИФИКАЦИЯ ДОКУМЕНТОВ ----------
DOC_TYPES = {
    "Пояснительная записка / ПД": ["пояснительная записка", "пз", "проектная документация", "пд№"],
    "ТЗ / задание на проектирование": ["задание на проектирование", "тз", "техническое задание"],
    "Инженерные изыскания": ["изыскани", "геологи", "гидрогеолог", "геодез", "экологическ"],
    "Уставные документы": ["устав", "бюджет", "смет", "график", "календарн"],
    "Горно-техническая часть": ["горн", "вскрыти", "система разработк", "рудник", "шахт", "ствол", "карьер"],
    "Промышленная безопасность": ["безопасн", "фнп", "ггэ", "экспертиз", "опасный производственный", "опо"],
    "ВОР / ведомости": ["ведомост", "вор", "объём работ", "объем работ", "спецификац"],
}

def classify_doc(name, text):
    blob = (name + " " + text[:5000]).lower()
    found = [t for t, keys in DOC_TYPES.items() if any(k in blob for k in keys)]
    return found or ["Прочее"]

# ---------- ЧЕК-ЛИСТ ГОТОВНОСТИ ----------
REQUIRED_DOCS = [
    ("Пояснительная записка / ПД", "Основной документ проекта. Если нет — закажите у проектировщика с СРО."),
    ("ТЗ / задание на проектирование", "Без ТЗ проектировщик не начнёт. Утвердите у заказчика."),
    ("Инженерные изыскания", "Геология/гидрогеология обязательны для подземных работ (грунты, обводнённость)."),
    ("Горно-техническая часть", "Система разработки, вскрытие, вентиляция — ядро проекта рудника."),
    ("Промышленная безопасность", "Раздел ПБ, ГГЭ — обязательно для ОПО."),
    ("Уставные документы", "Устав, бюджет, график — без них проект неуправляем."),
    ("ВОР / ведомости", "Нужны для контроля объёмов и оптимизации затрат."),
]

def readiness_check(doc_types_present, project):
    out = []
    for dt, advice in REQUIRED_DOCS:
        if dt in doc_types_present:
            out.append((dt, "ok", ""))
        else:
            out.append((dt, "miss", advice))
    extra = []
    if project.get("underground"):
        extra.append(("Проект вентиляции / ГВУ", "miss" if "вентиляц" not in " ".join(doc_types_present) else "ok",
                      "Для подземных работ обязателен проект проветривания и ГВУ."))
        extra.append(("ПЛА (план ликвидации аварий)", "miss",
                      "Составляется до начала эксплуатации, согласовывается с ВГСЧ."))
    if project.get("blasting"):
        extra.append(("Решение по ВМ (склад/площадка + лицензия ВПХО)", "miss",
                      "Определитесь: площадка перегрузки или склад ВМ. Без лицензии ВПХО работы с ВМ невозможны."))
    if not project.get("infrastructure"):
        extra.append(("Инфраструктура (АБК, ГСМ, РММ)", "miss",
                      "Предусмотрите отдельный проект инфраструктуры под негосэкспертизу — не утяжеляйте основной."))
    if project.get("new_project"):
        extra.append(("Обогатительная фабрика", "miss",
                      "Переработка не предусмотрена. Если руду нужно обогащать — требуется отдельный проект ОФ "
                      "и хвостового хозяйства (отдельные ОПО). Или отгрузка сырой руды на сторону по договору."))
    return out, extra

# ---------- ПОИСК ПО БАЗЕ ЗНАНИЙ ----------
def search_knowledge(query, top_n=3):
    q_words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 3]
    if not q_words:
        return []
    results = []
    for d in S.docs:
        text = d.get("text", "")
        if not text:
            continue
        chunks = [text[i:i+600] for i in range(0, min(len(text), 100000), 500)]
        best, best_score = "", 0
        for ch in chunks:
            score = sum(1 for w in q_words if w in ch.lower())
            if score > best_score:
                best, best_score = ch, score
        if best_score > 0:
            results.append((best_score, d["name"], best))
    results.sort(key=lambda x: -x[0])
    return results[:top_n]

# ---------- ИНЖЕНЕРНАЯ ЛОГИКА ----------
def build_requirements(p):
    reqs = []
    if p.get("underground"):
        reqs += [
            "Подземные горные работы → объект относится к ОПО (для шахт/рудников, как правило, I класса опасности)",
            "Регистрация ОПО в реестре Ростехнадзора",
            "Технический проект разработки (утверждение — условие лицензии на недра, обычно ≤24 мес. с регистрации)",
            "Экспертиза ГГЭ (промышленная безопасность) — обязательна для подземных работ",
            "Проект вентиляции / ГВУ, паспорта крепления, ПЛА",
            "Если БВР → лицензия ВПХО и решение по хранению/перегрузке ВМ",
        ]
    if p.get("open_pit"):
        reqs += [
            "Открытые горные работы → классификация ОПО по объёму добычи",
            "План развития горных работ (ПГР) с согласованием Ростехнадзора",
            "При БВР → лицензия ВПХО, паспорт БВР, склад/площадка ВМ",
            "ГГЭ для объектов, на которые распространяются ФНП",
        ]
    return reqs

def decomposition_advice(p):
    return ("💡 ОПТИМИЗАЦИЯ: инфраструктуру (склады ГСМ, РММ, АБК, гараж, депо) вынесите в отдельный проект "
            "под негосударственную экспертизу — основной проект станет легче, сроки экспертизы сократятся на месяцы. "
            "Проверено практикой: так сделано на Шайтанском руднике (ООО «МРК») — I этап инфраструктуры отдельным проектом 6601.002.17.")

# ---------- DWG-АНАЛИЗ (PRO) ----------
def analyze_dwg(text, name):
    recs = []
    t = text.lower()
    if "лоток" in t:
        recs.append("🔧 Кабельные лотки: проверьте толщину 2,5 мм → 1,5 мм на непроходных участках (экономия металла до 40%, проверить ПУЭ и нагрузку).")
    if "кабел" in t:
        recs.append("🔧 Сечения кабелей: часто заложен запас — проверьте возможность уменьшения на 1 ступень.")
    if "металлоконструкц" in t or "мк" in t:
        recs.append("🔧 Металлоконструкции: типовые серийные решения вместо индивидуальных — экономия 10–20%.")
    if "трубопровод" in t:
        recs.append("🔧 Трубопроводы: пересчитайте толщину стенки по коррозионному износу.")
    if not recs:
        recs.append("Извлечённый из DWG текст ограничен. Полный анализ чертежей (размеры, спецификации) доступен при подключении ИИ-модуля распознавания.")
    return "\n".join(recs)

# ---------- ГЕНЕРАТОРЫ ДОКУМЕНТОВ ----------
def gen_charter(p):
    return (
        "УСТАВ ПРОЕКТА\n"
        f"1. Название: {p.get('name')}\n"
        f"2. Цель: {'вскрытие и отработка месторождения' if p.get('new_project') else 'реализация проекта'} "
        f"({'подземный' if p.get('underground') else 'открытый' if p.get('open_pit') else ''} способ)\n"
        "3. Границы: от ИРД до ввода в эксплуатацию\n"
        "4. Критерии успеха: заключения ГГЭ/ГЭЭ, ввод в мощность, бюджет ±10%\n"
        "5. Роль РП: координация подрядчиков, сроки, бюджет, коммуникация с надзором\n"
        "6. Ограничения: ФНП, лицензионные условия, экология\n"
    )

def gen_schedule(p):
    stages = [("ИРД и лицензирование", 3), ("ТЗ и изыскания", 4),
              ("Техпроект / проектная документация", 6), ("Экспертизы ГГЭ/ГЭЭ", 4),
              ("Рабочая документация", 6), ("Строительство", 12), ("Пусконаладка и ввод", 3)]
    lines = ["ГРАФИК ПРОЕКТА (месяцы):"]
    t = 1
    for n, d in stages:
        lines.append(f"  Мес. {t:>2}–{t+d-1:>2}: {n}")
        t += d
    lines.append(f"  ИТОГО: ~{t-1} мес. (уточнить при наличии календарного плана)")
    return "\n".join(lines)

def gen_budget(p):
    return ("БЮДЖЕТ (укрупнённо, уточняется сметой):\n"
            "  • Проектирование и экспертизы\n  • Горно-капитальные работы\n"
            "  • Оборудование (подъём, вентиляция, самоходная техника)\n"
            "  • Инфраструктура (отдельный проект)\n  • Резерв 10%\n"
            "⚠️ Смета не разрабатывалась — включите в план как приоритетную задачу.")

# ============================================================
#  GREENFIELD COMMAND CENTER (встроенный модуль)
# ============================================================
BASE_DOCUMENTS = [
    ("Устав проекта", "Управление", "Обязателен внутренним контуром", "Фиксирует цель, границы, команду, сроки, бюджет и риски."),
    ("Календарный план-график / WBS", "Управление", "Обязателен", "Базовый план, логические связи, критический путь, ресурсы."),
    ("Бюджет / план финансирования", "Финансы", "Обязателен", "CAPEX/OPEX, резерв, финансирование по годам и объектам."),
    ("Реестр ИРД", "Исходные данные", "Обязателен", "Владелец, срок, статус, влияние на проектирование/экспертизы."),
    ("Права на землю / земельно-имущественные документы", "ИРД", "Проверить применимость", "Площадки, трассы коммуникаций, отвалы, объекты инфраструктуры."),
    ("Инженерные изыскания", "ИРД", "По составу объекта", "ИГИ, ИГДИ, ИЭИ, ИГМИ; для горных работ — геомеханика и гидрогеология."),
    ("Технические условия", "ИРД", "По необходимости", "Электроснабжение, вода, связь, примыкания, иные внешние подключения."),
]

def requirement_matrix(p):
    rows = [{"name": n, "group": g, "need": need, "reason": reason, "confidence": "Проверить экспертом"}
            for n, g, need, reason in BASE_DOCUMENTS]

    def add(name, group, need, reason, confidence="По ответам мастера"):
        rows.append({"name": name, "group": group, "need": need, "reason": reason, "confidence": confidence})

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

    if p.get("capital_construction"):
        add("Проектная документация (ПД) по составу ПП РФ №87", "Проектирование", "Требуется",
            "Для объектов капитального строительства: состав разделов определяется объектом, заданием и применимыми требованиями.")
        add("Рабочая документация (РД)", "Проектирование", "Требуется для производства работ",
            "Детализация решений ПД для закупок, СМР, монтажа и исполнительной документации.")
        add("Проект организации строительства (ПОС)", "ПД по №87", "Как правило требуется", "Планирование организации, очередности и безопасности строительства.")
        add("Сметная документация", "ПД / финансы", "Проверить необходимость", "Состав зависит от источника финансирования и решения заказчика.")

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
        add("Проектные решения по БВР, ВМ и площадке/складу ВМ", "Промышленная безопасность", "Требуется",
            "Определить схему снабжения ВМ и применимые разрешительные требования.")
    if p.get("water_discharge"):
        add("Водохозяйственные решения, водоотлив, очистка и сброс", "Экология/вода", "Требуется",
            "Шахтные, карьерные и поверхностные воды; проверить водный объект и разрешительные процедуры.")
    if p.get("tailings"):
        add("Проект хвостового хозяйства / ГТС, декларация безопасности, мониторинг", "ГТС", "Требуется",
            "Хвостохранилище и связанные ГТС требуют отдельной технической и разрешительной проработки.")
    if p.get("infrastructure"):
        add("Отдельные ТЗ и ПД локальных объектов инфраструктуры", "Проектирование", "Рекомендуется",
            "ВП, РММ, ЛЭП, дороги, котельная, ГСМ, связь — выделять в управляемые пакеты работ.")
    return rows

def make_roadmap(p):
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

def roadmap_health(tasks, docs):
    critical_docs = [x for x in docs if x["need"] in {"Критично", "Требуется"}]
    end = max((x["finish"] for x in tasks), default=date.today())
    return {"tasks": len(tasks), "critical": sum(x["critical"] for x in tasks),
            "docs": len(docs), "critical_docs": len(critical_docs), "forecast_end": end}

def hero(project_name, subtitle):
    st.markdown(
        f'<section class="cc-hero"><h1>⛏ {project_name or "Новый greenfield-проект"}</h1>'
        f'<p>{subtitle}</p></section>', unsafe_allow_html=True)

def chip(label, kind="info"):
    return f'<span class="cc-chip chip-{kind}">{label}</span>'

def greenfield_intake():
    st.subheader("🧭 Диагностика greenfield-проекта")
    st.caption("Займет 5–7 минут. Можно выбирать «неизвестно»: система создаст задачу на уточнение.")
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

def render_dashboard(project, tasks, docs):
    health = roadmap_health(tasks, docs)
    hero(project.get("project_name", "Greenfield-проект"),
         f"{project.get('company') or 'Заказчик не указан'} · {project.get('region') or 'Регион не указан'}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Работ в дорожной карте", health["tasks"])
    c2.metric("Критических работ", health["critical"])
    c3.metric("Требований к документам", health["docs"])
    c4.metric("Прогноз завершения", health["forecast_end"].strftime("%d.%m.%Y"))

    blockers = []
    if not project.get("has_license"):
        blockers.append("Подтвердить лицензию и ее условия")
    if not project.get("reserves_approved"):
        blockers.append("Подтвердить запасы / маршрут их утверждения")
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

def render_requirements(docs):
    st.subheader("📚 Матрица документации и экспертиз")
    groups = sorted({x["group"] for x in docs})
    selected = st.multiselect("Фильтр по блоку", groups, default=groups)
    for row in [x for x in docs if x["group"] in selected]:
        kind = "risk" if row["need"] == "Критично" else "warn" if row["need"] in {"Требуется", "Как правило требуется"} else "info"
        with st.expander(f"{row['group']} · {row['name']} · {row['need']}"):
            st.markdown(chip(row["need"], kind) + chip(row["confidence"], "info"), unsafe_allow_html=True)
            st.write(row["reason"])
            st.caption("Решение о применимости фиксируется ответственным экспертом в карточке требования.")

# ---------- УТИЛИТА ПРИВЕДЕНИЯ ДАТ (фикс ошибки data_editor) ----------
def _ensure_roadmap_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит столбцы дат к datetime для st.data_editor (DateColumn)."""
    if df is None or len(df) == 0:
        return df
    df = df.copy()
    for col in ["Начало", "Окончание"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if {"Начало", "Окончание"}.issubset(df.columns):
        df = df[~(df["Начало"].isna() & df["Окончание"].isna())]
    return df

def _tasks_to_df(tasks):
    rows = [{"ID": t["id"], "Работа": t["work"], "Фаза": t["phase"], "Ответственный": t["owner"],
             "Начало": t["start"], "Окончание": t["finish"], "Длительность, дн": t["duration"],
             "Предшественники": ", ".join(t["predecessors"]) or "—",
             "Критично": "Да" if t["critical"] else "Нет",
             "Статус": t["status"]}
            for t in tasks]
    return pd.DataFrame(rows)

STATUS_OPTIONS = ["Не начато", "В работе", "Завершено", "Отложено"]

def render_roadmap():
    st.subheader("🧭 Дорожная карта (редактируемая)")
    st.caption("Даты рассчитаны от целевой даты старта. Правьте сроки, статусы и ответственных прямо в таблице.")

    if S.roadmap is None or len(S.roadmap) == 0:
        if S.gf_tasks:
            S.roadmap = _tasks_to_df(S.gf_tasks)
        else:
            st.info("Сначала пройдите диагностику в разделе «🗺 Greenfield command center» — дорожная карта построится автоматически.")
            return

    roadmap_df = _ensure_roadmap_dates(S.roadmap)

    edited = st.data_editor(
        roadmap_df,
        num_rows="dynamic",
        use_container_width=True,
        key="roadmap_editor",
        column_config={
            "Начало": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Окончание": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Статус": st.column_config.SelectboxColumn(options=STATUS_OPTIONS),
            "Критично": st.column_config.SelectboxColumn(options=["Да", "Нет"]),
        },
    )
    S.roadmap = edited

    done = int((edited["Статус"] == "Завершено").sum())
    st.progress(done / len(edited) if len(edited) else 0, f"Завершено: {done} из {len(edited)}")

    if st.button("⬇️ Скачать дорожную карту (CSV)"):
        csv = edited.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Сохранить CSV", csv, "roadmap.csv", "text/csv")

def greenfield_page(state):
    if not state.gf_project:
        hero("Greenfield command center", "От лицензии и запасов до ввода объекта в эксплуатацию")
        data = greenfield_intake()
        if data:
            state.gf_project = data
            state.gf_tasks = make_roadmap(data)
            state.gf_requirements = requirement_matrix(data)
            state.roadmap = None  # пересоберём из новых задач
            st.rerun()
        return

    page = st.radio("Раздел", ["Рабочий стол", "Дорожная карта", "Документация и экспертизы", "Перепройти диагностику"], horizontal=True)
    if page == "Рабочий стол":
        render_dashboard(state.gf_project, state.gf_tasks, state.gf_requirements)
    elif page == "Дорожная карта":
        render_roadmap()
    elif page == "Документация и экспертизы":
        render_requirements(state.gf_requirements)
    else:
        state.gf_project = {}
        state.gf_tasks = []
        state.gf_requirements = []
        state.roadmap = None
        st.rerun()

# ============================================================
#  ИНТЕРФЕЙС
# ============================================================
st.title("⛏ Горный Дельта")
st.caption("ИИ-платформа руководителя проектов горнодобывающего предприятия • v2.1")

user_id = st.sidebar.text_input("Ваш ID / e-mail", value="guest")

menu = st.sidebar.radio("Навигация", [
    "🗺 Greenfield command center",
    "🚀 Новый проект (мастер)",
    "📂 Документы проекта",
    "✅ Чек-лист готовности",
    "🧠 Инженерная логика",
    "💬 Ассистент (база знаний)",
    "📋 Уставные документы",
    "📐 PRO: анализ DWG",
    "💳 Подписка",
    "🔐 Кабинет владельца",
])

# ---------- GREENFIELD ----------
if menu.startswith("🗺"):
    greenfield_page(S)

# ---------- МАСТЕР ----------
elif menu.startswith("🚀"):
    st.header("Создание проекта — Шаг 1: параметры")
    with st.form("wizard"):
        name = st.text_input("Название проекта", "")
        c1, c2 = st.columns(2)
        with c1:
            underground = st.checkbox("Подземные горные работы")
            open_pit = st.checkbox("Открытые горные работы")
            blasting = st.checkbox("Применяются БВР", True)
        with c2:
            infrastructure = st.checkbox("Инфраструктура уже есть/предусмотрена (АБК, ГСМ, РММ...)")
            has_files = st.checkbox("Есть исходные файлы (ПД, ТЗ, изыскания...)")
            new_project = st.checkbox("Проект новый (с нуля)")
        volume = st.number_input("Объём добычи, т/год (если известен)", value=500000, step=50000)
        submitted = st.form_submit_button("➡️ Создать проект")
    if submitted and name:
        S.project = {"name": name, "underground": underground, "open_pit": open_pit,
                     "blasting": blasting, "infrastructure": infrastructure,
                     "has_files": has_files, "new_project": new_project, "volume": volume}
        S.wizard_done = True
        log_request(user_id, "wizard", json.dumps(S.project, ensure_ascii=False))
        st.success(f"Проект «{name}» создан! Переходите в раздел «📂 Документы проекта».")
        if not has_files:
            st.info("У вас нет исходных файлов — начните с ТЗ на проектирование и инженерных изысканий. "
                    "Раздел «✅ Чек-лист готовности» подскажет полный список.")
    elif S.wizard_done:
        p = S.project
        st.info(f"Текущий проект: «{p['name']}» — "
                f"{'подземные ' if p['underground'] else ''}{'открытые ' if p['open_pit'] else ''}"
                f"работы, {p['volume']:,} т/год".replace(",", " "))
        if st.button("🔄 Начать новый проект"):
            S.wizard_done = False
            S.docs = []
            S.project = None
            st.rerun()

# ---------- ДОКУМЕНТЫ ----------
elif menu.startswith("📂"):
    st.header("Шаг 2: загрузка документов проекта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        st.caption("Загружайте всё, что есть: ПД, ТЗ, изыскания, устав, ВОР, DWG. "
                   "Система учится на ваших документах — база знаний пополняется.")
        files = st.file_uploader(
            "Выберите файлы",
            type=["pdf", "docx", "txt", "md", "csv", "xlsx", "dwg"],
            accept_multiple_files=True)
        if files:
            for f in files:
                text = extract_text(f)
                types = classify_doc(f.name, text)
                safe_name = f"{datetime.datetime.now():%Y%m%d%H%M%S}_{f.name}"
                try:
                    with open(os.path.join(DOCS_DIR, safe_name), "wb") as out:
                        out.write(f.getvalue())
                except Exception:
                    pass
                S.docs.append({"name": f.name, "text": text, "types": types})
                log_request(user_id, "upload", f.name, ",".join(types))
            st.success(f"Загружено файлов: {len(files)}. База знаний обновлена.")
        if S.docs:
            st.subheader(f"В базе знаний: {len(S.docs)} документов")
            for d in S.docs:
                with st.expander(f"📄 {d['name']} — {', '.join(d['types'])}"):
                    st.text(d["text"][:1500] or "[текст не извлечён]")

# ---------- ЧЕК-ЛИСТ ----------
elif menu.startswith("✅"):
    st.header("Шаг 3: чек-лист готовности проекта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        present = set()
        for d in S.docs:
            present.update(d["types"])
        base, extra = readiness_check(present, S.project)
        st.subheader("Обязательный состав документации")
        ok = sum(1 for _, s, _ in base if s == "ok")
        st.progress(ok / len(base) if base else 0, f"Готовность: {ok} из {len(base)}")
        for dt, status, advice in base:
            if status == "ok":
                st.markdown(f"✅ **{dt}** — загружено")
            else:
                st.markdown(f"⚠️ **{dt}** — отсутствует")
                if advice:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;→ {advice}")
        if extra:
            st.subheader("Отраслевые требования (по параметрам проекта)")
            for dt, status, advice in extra:
                if status == "ok":
                    st.markdown(f"✅ **{dt}**")
                else:
                    st.markdown(f"⚠️ **{dt}** — требуется")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;→ {advice}")

# ---------- ИНЖЕНЕРНАЯ ЛОГИКА ----------
elif menu.startswith("🧠"):
    st.header("Инженерная логика: требования к проекту")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        if st.button("Построить цепочку требований"):
            log_request(user_id, "logic", json.dumps(S.project, ensure_ascii=False))
            reqs = build_requirements(S.project)
            st.markdown("**Цепочка обязательных требований:**")
            for i, r in enumerate(reqs, 1):
                st.markdown(f"{i}. {r}")
            st.info(decomposition_advice(S.project))

# ---------- АССИСТЕНТ ПО БАЗЕ ЗНАНИЙ ----------
elif menu.startswith("💬"):
    st.header("Ассистент по базе знаний проекта")
    if not S.docs:
        st.info("База знаний пуста. Загрузите документы в разделе «📂 Документы проекта» — "
                "ассистент отвечает на основе ВАШИХ документов (принцип: только факты из базы).")
    else:
        st.caption(f"База знаний: {len(S.docs)} документов. Задайте вопрос — ответ будет с цитатами из ваших файлов.")
        q = st.text_input("Ваш вопрос", placeholder="Например: какая система разработки принята? какие стволы предусмотрены?")
        if st.button("Спросить") and q.strip():
            log_request(user_id, "ask", q)
            results = search_knowledge(q)
            if results:
                for score, fname, frag in results:
                    st.markdown(f"**📄 {fname}:**")
                    st.info(frag.strip()[:800])
                st.caption("Ответ построен на фрагментах загруженных документов. "
                           "Полноценные генеративные ответы — при подключении ИИ-модели (следующий этап).")
            else:
                st.warning("В загруженных документах не найдено релевантной информации. "
                           "Попробуйте другие формулировки или загрузите дополнительные документы.")

# ---------- УСТАВНЫЕ ----------
elif menu.startswith("📋"):
    st.header("Уставные документы")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        doc = st.radio("Документ", ["Устав", "График", "Бюджет"])
        if st.button("Сгенерировать"):
            log_request(user_id, "charter", doc)
            fn = {"Устав": gen_charter, "График": gen_schedule, "Бюджет": gen_budget}[doc]
            st.code(fn(S.project), language="text")

# ---------- DWG (PRO) ----------
elif menu.startswith("📐"):
    st.header("PRO: анализ DWG-чертежей")
    if S.plan != "pro":
        st.warning("🔒 Анализ DWG-файлов — платная функция тарифа PRO "
                   f"({PRICE_PRO} ₽/мес). Активируйте в разделе «Подписка».")
    else:
        f = st.file_uploader("Загрузите DWG-файл", type=["dwg"])
        if f and st.button("📐 Проанализировать чертёж"):
            log_request(user_id, "dwg", f.name)
            text = extract_text(f)
            st.markdown("**Извлечённые данные:**")
            st.text(text[:2000] or "[текст не извлечён]")
            st.markdown("**Рекомендации по оптимизации:**")
            st.markdown(analyze_dwg(text, f.name))
            st.caption("Рекомендации консультационные — финальную проверку выполняет проектировщик.")

# ---------- ПОДПИСКА ----------
elif menu.startswith("💳"):
    st.header("Подписка")
    st.markdown(f"**Базовая** — {PRICE_BASIC} ₽/мес: мастер, документы, чек-лист, база знаний, уставные документы.")
    st.markdown(f"**PRO** — {PRICE_PRO} ₽/мес: + анализ DWG-чертежей и ВОР с рекомендациями по оптимизации.")
    promo = st.text_input("Промокод").strip().upper()
    if st.button("Активировать"):
        log_request(user_id, "billing", f"promo={promo}")
        if promo in PROMO_CODES:
            S.plan = PROMO_CODES[promo]
            st.success(f"Активирован тариф: {PROMO_CODES[promo].upper()}")
        else:
            st.error("Неверный промокод.")

# ---------- КАБИНЕТ ВЛАДЕЛЬЦА ----------
elif menu.startswith("🔐"):
    st.header("Кабинет владельца")
    if not S.show_owner:
        pwd = st.text_input("Пароль владельца", type="password")
        if st.button("Войти") and pwd == OWNER_PASSWORD:
            S.show_owner = True
            st.rerun()
    if S.show_owner:
        entries = read_log()
        st.subheader(f"Журнал: {len(entries)} записей")
        users = {}
        for e in entries:
            users.setdefault(e["user"], []).append(e)
        for u, es in users.items():
            with st.expander(f"{u} — {len(es)} действий"):
                st.markdown("**Психологический портрет:**")
                st.markdown(psych_profile(es))
                st.markdown("**История:**")
                for e in es[-20:]:
                    st.text(f"[{e['ts']}] ({e['mode']}) {e['text'][:120]}")
        st.subheader("База знаний (файлы на сервере)")
        for fn in sorted(os.listdir(DOCS_DIR)):
            st.text(fn)

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 [Владелец продукта]. Все права защищены.")
