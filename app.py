# ============================================================
#  ГОРНЫЙ ДЕЛЬТА v3.0 — ИИ-платформа руководителя проектов
#  (горнодобывающие предприятия: открытые и подземные работы)
# ============================================================
#  СЦЕНАРИЙ РАБОТЫ:
#   ШАГ 0. Концепция освоения месторождения:
#          A) Полный комплекс (рудник/карьер + инфраструктура + ОФ)
#          B) Добыча + инфраструктура (сырая руда на сторону)
#          C) Только добычное предприятие
#   ШАГ 1. Мастер: параметры (подземка/карьер, БВР, объём добычи)
#   ШАГ 2. Загрузка документов (ПД, ТЗ, изыскания, уставные, ВОР,
#          шаблон устава пользователя)
#   ШАГ 3. График освоения по мастер-шаблону (зависимости операций)
#   ШАГ 4. Дорожная карта «глупому РП»: что делать прямо сейчас
#   ШАГ 5. PRO: анализ DWG-файлов (платно для пользователей)
# ============================================================
#  ЗАПУСК ЛОКАЛЬНО:   pip install streamlit pypdf python-docx openpyxl
#                     streamlit run app.py
# ============================================================

import streamlit as st
import json
import os
import datetime
import re

# ---------- НАСТРОЙКИ ВЛАДЕЛЬЦА ----------
OWNER_PASSWORD = "CHANGE_ME_2026"
PRICE_BASIC = 4900        # ₽/мес
PRICE_PRO = 14900         # ₽/мес (включая DWG-анализ)
PROMO_CODES = {"PILOT2026": "pro", "DEMO": "basic"}
LOG_FILE = "users_log.jsonl"
DOCS_DIR = "knowledge"
os.makedirs(DOCS_DIR, exist_ok=True)
# ---------------------------------------------------------------

st.set_page_config(page_title="Горный Дельта — ИИ-платформа РП", page_icon="⛏", layout="wide")

# ---------- СОСТОЯНИЕ ----------
S = st.session_state
defaults = {
    "plan": "free",
    "show_owner": False,
    "wizard_done": False,
    "project": None,
    "docs": [],
    "messages": [],
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

# ============================================================
#  МАСТЕР-ШАБЛОН ГРАФИКА ОСВОЕНИЯ МЕСТОРОЖДЕНИЯ
# ============================================================
# Операция: (id, название, стадия, длительность мес, зависит_от[])
# Длительности — базовые оценки, корректируются параметрами проекта.

def get_master_template():
    """Мастер-шаблон комплексного графика освоения месторождения."""
    ops = [
        # --- Стадия 0. Лицензирование / ИРД ---
        ("LIC", "Оформление права пользования недрами (получено/переоформление лицензии)", "Лицензирование", 3, []),
        ("IRD", "ИРД: анализ лицензионных обязательств и границ горного отвода", "Лицензирование", 2, ["LIC"]),
        # --- Стадия 1. ГРР ---
        ("GR1", "Доразведка: задание на доразведку и договор с подрядчиком", "ГРР", 2, ["IRD"]),
        ("GR2", "Полевые работы доразведки (бурение, опробование)", "ГРР", 8, ["GR1"]),
        ("GR3", "Подсчёт запасов, перевод в промышленные категории", "ГРР", 3, ["GR2"]),
        ("GR4", "Утверждение запасов ГКЗ/централизованная экспертиза", "ГРР", 4, ["GR3"]),
        # --- Стадия 2. ПИР ---
        ("TZ",  "ТЗ на проектирование (утверждение у застройщика)", "ПИР", 2, ["GR4"]),
        ("IZK", "Инженерные изыскания (геология, гидрогеология, геодезия)", "ПИР", 4, ["GR4"]),
        ("TEO", "ТЭО / ТЭО кондиций, выбор способа разработки", "ПИР", 3, ["TZ", "IZK"]),
        ("PI",  "Проектная документация (техпроект разработки)", "ПИР", 8, ["TEO"]),
        ("EXE", "Экспертиза: ГГЭ (ОПО) и/или ГЭЭ", "ПИР", 4, ["PI"]),
        ("RD",  "Рабочая документация (первые очереди)", "ПИР", 6, ["EXE"]),
        # --- Стадия 3. Реализация ---
        ("GKR", "Горно-капитальные работы (вскрытие, подготовка)", "Реализация", 12, ["RD"]),
        ("SBO", "Заказ и поставка основного оборудования", "Реализация", 10, ["EXE"]),
        ("SMR", "СМР поверхностного комплекса", "Реализация", 12, ["RD"]),
        ("PNR", "Пусконаладочные работы, опытная эксплуатация", "Реализация", 3, ["GKR", "SBO", "SMR"]),
        ("OPO", "Регистрация ОПО в реестре Ростехнадзора", "Реализация", 2, ["EXE"]),
        ("VVD", "Ввод в эксплуатацию / начало добычи", "Реализация", 1, ["PNR", "OPO"]),
        # --- Стадия 4. Эксплуатация ---
        ("EKS", "Промышленная эксплуатация (добыча)", "Эксплуатация", 240, ["VVD"]),
        # --- Стадия 5. Вывод из эксплуатации ---
        ("ZAK", "Ликвидация/консервация, рекультивация", "Вывод из эксплуатации", 24, ["EKS"]),
    ]
    return ops

# Блоки, зависящие от концепции
def extra_blocks(concept, p):
    """Дополнительные блоки операций по концепции освоения."""
    ops = []
    if concept in ("full", "infra"):
        # Инфраструктура — отдельный проект, негосэкспертиза
        ops += [
            ("INF1", "ТЗ и ПД инфраструктуры (АБК, ГСМ, РММ, энерго) — отдельный проект", "Реализация", 5, ["TZ"]),
            ("INF2", "Экспертиза инфраструктуры (негосударственная)", "Реализация", 2, ["INF1"]),
            ("INF3", "СМР инфраструктуры", "Реализация", 10, ["INF2"]),
        ]
    if concept == "full":
        # Обогатительная фабрика + хвостовое хозяйство — отдельные ОПО
        ops += [
            ("OF1", "ТЗ и ПД обогатительной фабрики", "Реализация", 7, ["TEO"]),
            ("OF2", "ГГЭ по ОФ и хвостовому хозяйству (ГТС)", "Реализация", 4, ["OF1"]),
            ("OF3", "СМР ОФ и хвостохранилища", "Реализация", 18, ["OF2"]),
            ("OF4", "ПНР и ввод ОФ", "Реализация", 4, ["OF3"]),
        ]
    if p.get("blasting"):
        ops += [
            ("VPHO", "Лицензия ВПХО, решение по хранению ВМ (склад/площадка)", "Лицензирование", 6, ["LIC"]),
            ("BVR", "Паспорта БВР, договор с специализированной организацией", "Реализация", 2, ["RD", "VPHO"]),
        ]
    if p.get("underground"):
        ops += [
            ("PLA", "Разработка ПЛА, договор с ВГСЧ", "Реализация", 4, ["RD"]),
        ]
    return ops

def generate_schedule(project):
    """Строит график по мастер-шаблону с учётом концепции и параметров."""
    concept = project.get("concept", "full")
    ops = get_master_template() + extra_blocks(concept, project)
    # корректировка длительностей
    scale = 1.0
    vol = project.get("volume", 500000)
    if vol >= 3_000_000:
        scale = 1.25
    elif vol <= 200_000:
        scale = 0.85
    if project.get("new_project"):
        pass  # полный цикл уже заложен
    else:
        # проект продолжается: лицензия и ГРР уже пройдены
        ops = [o for o in ops if o[0] not in ("LIC", "IRD", "GR1", "GR2", "GR3", "GR4")]

    # расчёт ранних стартов (критический путь, месяцы)
    dur = {o[0]: max(1, round(o[3] * scale)) for o in ops}
    deps = {o[0]: o[4] for o in ops}
    names = {o[0]: o[1] for o in ops}
    stages = {o[0]: o[2] for o in ops}
    start, finish = {}, {}
    def calc(oid):
        if oid in start:
            return start[oid]
        start[oid] = finish[oid] = 0
        for d in deps[oid]:
            if d in dur:
                calc(d)
                start[oid] = max(start[oid], finish[d])
        finish[oid] = start[oid] + dur[oid]
        return start[oid]
    for o in ops:
        calc(o[0])
    order = sorted(ops, key=lambda o: (start[o[0]], finish[o[0]]))
    rows = []
    for o in order:
        oid = o[0]
        rows.append({
            "id": oid, "операция": names[oid], "стадия": stages[oid],
            "старт": start[oid] + 1, "финиш": finish[oid],
            "длительность": dur[oid],
            "зависимости": ", ".join(deps[oid]) or "—",
        })
    total = max(finish.values()) if finish else 0
    # эксплуатация не входит в срок освоения
    total_dev = max((r["финиш"] for r in rows if r["стадия"] != "Эксплуатация"
                     and r["стадия"] != "Вывод из эксплуатации"), default=0)
    return rows, total_dev, total

CONCEPTS = {
    "full": "Полный комплекс: рудник/карьер + инфраструктура + обогатительная фабрика",
    "infra": "Добыча + инфраструктура (сырая руда на сторону по договору)",
    "mining": "Только добычное предприятие (переработка и инфраструктура не в проекте)",
}

# ---------- ДОРОЖНАЯ КАРТА ----------
def build_roadmap(p, rows):
    concept = p.get("concept", "full")
    first_ops = [r for r in rows if r["стадия"] in ("Лицензирование", "ГРР", "ПИР")]
    steps = [
        ("ПРЯМО СЕЙЧАС (первые 2 недели)",
         "1. Соберите лицензию и условия пользования недрами — проверьте сроки обязательств "
         "(техпроект обычно ≤24 мес. с регистрации лицензии!).\n"
         "2. Изучите, в каких категориях запасы — если B/C1 мало, готовьте задание на доразведку.\n"
         "3. Назначьте проектировщика с действующим СРО.\n"
         "4. Начните вести реестр документов проекта (этот раздел — «Документы»)."),
        ("БЛИЖАЙШИЙ ГОД",
         "• ТЗ на проектирование → инженерные изыскания → ТЭО.\n"
         "• Решите вопрос БВР: лицензия ВПХО, склад или площадка перегрузки ВМ.\n"
         "• Определите организационную модель: свой подрядчик или EPC.\n"
         "• Смета и бюджет — закажите одновременно с ТЭО."),
        ("СТРАТЕГИЯ",
         (f"Выбрана концепция: {CONCEPTS[concept]}.\n"
          + ("Инфраструктуру вынесите в отдельный проект под негосэкспертизу — "
             "основной проект станет легче и пройдёт экспертизу быстрее.\n" if concept != "mining" else "")
          + ("ОФ и хвостовое хозяйство — отдельные ОПО: планируйте их ГГЭ заранее.\n" if concept == "full" else "")
          + ("Договор на поставку сырой руды — ключевое условие концепции: начните переговоры с покупателем сразу.\n" if concept == "infra" else "")
          + f"Ориентировочный срок до ввода в эксплуатацию: ~{sum(1 for _ in rows)} операций, см. график выше.")),
    ]
    return steps

# ---------- КЛАССИФИКАЦИЯ ДОКУМЕНТОВ ----------
DOC_TYPES = {
    "Пояснительная записка / ПД": ["пояснительная записка", "пз", "проектная документация", "пд№"],
    "ТЗ / задание на проектирование": ["задание на проектирование", "тз", "техническое задание"],
    "Инженерные изыскания": ["изыскани", "геологи", "гидрогеолог", "геодез", "экологическ"],
    "Уставные документы": ["устав", "бюджет", "смет", "график", "календарн"],
    "Горно-техническая часть": ["горн", "вскрыти", "система разработк", "рудник", "шахт", "ствол", "карьер"],
    "Промышленная безопасность": ["безопасн", "фнп", "ггэ", "экспертиз", "опасный производственный", "опо"],
    "ВОР / ведомости": ["ведомост", "вор", "объём работ", "объем работ", "спецификац"],
    "Шаблон устава": ["устав проекта", "шаблон устава"],
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
        out.append((dt, "ok" if dt in doc_types_present else "miss", advice if dt not in doc_types_present else ""))
    extra = []
    if project.get("underground"):
        extra.append(("Проект вентиляции / ГВУ", "miss" if "вентиляц" not in " ".join(doc_types_present) else "ok",
                      "Для подземных работ обязателен проект проветривания и ГВУ."))
        extra.append(("ПЛА (план ликвидации аварий)", "miss",
                      "Составляется до начала эксплуатации, согласовывается с ВГСЧ."))
    if project.get("blasting"):
        extra.append(("Решение по ВМ (склад/площадка + лицензия ВПХО)", "miss",
                      "Без лицензии ВПХО работы с ВМ невозможны."))
    if project.get("concept") == "full":
        extra.append(("Обогатительная фабрика", "miss",
                      "ОФ и хвостовое хозяйство — отдельные ОПО, отдельный проект и ГГЭ."))
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
    concept = p.get("concept", "full")
    if concept == "full":
        reqs.append("Концепция «полный комплекс»: три проекта в одном портфеле — добыча, инфраструктура, ОФ. "
                    "Каждый со своей экспертизой и графиком.")
    elif concept == "infra":
        reqs.append("Концепция «добыча + инфраструктура»: ключевая задача — долгосрочный договор на сбыт сырой руды.")
    else:
        reqs.append("Концепция «только добыча»: проверьте, кто обеспечивает переработку и инфраструктуру.")
    if p.get("underground"):
        reqs += [
            "Подземные горные работы → ОПО (обычно I класса опасности), регистрация в реестре Ростехнадзора",
            "Техпроект разработки — условие лицензии (обычно ≤24 мес. с регистрации)",
            "ГГЭ обязательна для подземных работ",
            "Проект вентиляции / ГВУ, паспорта крепления, ПЛА",
            "Если БВР → лицензия ВПХО и решение по хранению/перегрузке ВМ",
        ]
    if p.get("open_pit"):
        reqs += [
            "Открытые горные работы → классификация ОПО по объёму добычи",
            "План развития горных работ (ПГР) с согласованием Ростехнадзора",
            "При БВР → лицензия ВПХО, паспорт БВР, склад/площадка ВМ",
        ]
    return reqs

def decomposition_advice(p):
    if p.get("concept") != "mining":
        return ("💡 ОПТИМИЗАЦИЯ: инфраструктуру (склады ГСМ, РММ, АБК, гараж, депо) вынесите в отдельный проект "
                "под негосударственную экспертизу — основной проект станет легче, сроки экспертизы сократятся на месяцы. "
                "Проверено практикой: так сделано на Шайтанском руднике (ООО «МРК») — I этап инфраструктуры отдельным проектом 6601.002.17.")
    return "💡 Концепция «только добыча»: убедитесь, что сбыт и инфраструктура покрыты договорами и чужими проектами."

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
        recs.append("Извлечённый из DWG текст ограничен. Полный анализ чертежей доступен при подключении ИИ-модуля распознавания.")
    return "\n".join(recs)

# ---------- ГЕНЕРАТОРЫ ДОКУМЕНТОВ ----------
def gen_charter(p, template_text=None):
    concept = CONCEPTS[p.get("concept", "full")]
    mine = "подземный" if p.get("underground") else "открытый" if p.get("open_pit") else ""
    base = (
        "УСТАВ ПРОЕКТА\n"
        f"1. Название: {p.get('name')}\n"
        f"2. Концепция освоения: {concept}\n"
        f"3. Цель: {'вскрытие и отработка месторождения' if p.get('new_project') else 'реализация проекта'} "
        f"({mine} способ, {p.get('volume', 0):,} т/год)\n".replace(",", " ")
        + "4. Границы: от ИРД до ввода в эксплуатацию\n"
        "5. Критерии успеха: заключения ГГЭ/ГЭЭ, ввод в мощность, бюджет ±10%\n"
        "6. Роль РП: координация подрядчиков, сроки, бюджет, коммуникация с надзором\n"
        "7. Ограничения: ФНП, лицензионные условия, экология\n"
    )
    if template_text:
        # подстановка параметров в шаблон пользователя
        subst = template_text
        for key, val in {"{НАЗВАНИЕ}": p.get("name", ""), "{КОНЦЕПЦИЯ}": concept,
                         "{ОБЪЕМ}": str(p.get("volume", "")), "{СПОСОБ}": mine,
                         "{ДАТА}": f"{datetime.date.today():%d.%m.%Y}"}.items():
            subst = subst.replace(key, val)
        return base + "\n--- ШАБЛОН ПОЛЬЗОВАТЕЛЯ (с подстановкой параметров) ---\n" + subst[:3000]
    return base

def gen_budget(p):
    concept = p.get("concept", "full")
    lines = ["БЮДЖЕТ (укрупнённо, уточняется сметой):",
             "  • Проектирование и экспертизы", "  • Горно-капитальные работы",
             "  • Оборудование (подъём, вентиляция, самоходная техника)"]
    if concept != "mining":
        lines.append("  • Инфраструктура (отдельный проект)")
    if concept == "full":
        lines.append("  • ОФ и хвостовое хозяйство (отдельный проект, отдельные ОПО)")
    lines += ["  • Резерв 10%",
              "⚠️ Смета не разрабатывалась — включите в план как приоритетную задачу."]
    return "\n".join(lines)

# ============================================================
#  ИНТЕРФЕЙС
# ============================================================
st.title("⛏ Горный Дельта")
st.caption("ИИ-платформа руководителя проектов горнодобывающего предприятия • v3.0")

user_id = st.sidebar.text_input("Ваш ID / e-mail", value="guest")

menu = st.sidebar.radio("Навигация", [
    "🚀 Новый проект (мастер)",
    "📅 График освоения",
    "🗺 Дорожная карта",
    "📂 Документы проекта",
    "✅ Чек-лист готовности",
    "🧠 Инженерная логика",
    "💬 Ассистент (база знаний)",
    "📋 Уставные документы",
    "📐 PRO: анализ DWG",
    "💳 Подписка",
    "🔐 Кабинет владельца",
])

# ---------- МАСТЕР ----------
if menu.startswith("🚀"):
    st.header("Создание проекта")
    st.subheader("Шаг 0: концепция освоения месторождения")
    st.caption("Главный выбор РП — от него зависит состав, стоимость и сроки всего проекта.")
    with st.form("wizard"):
        concept = st.radio("Концепция", list(CONCEPTS.keys()),
                           format_func=lambda k: CONCEPTS[k])
        name = st.text_input("Название проекта", "")
        c1, c2 = st.columns(2)
        with c1:
            underground = st.checkbox("Подземные горные работы")
            open_pit = st.checkbox("Открытые горные работы")
            blasting = st.checkbox("Применяются БВР", True)
        with c2:
            new_project = st.checkbox("Проект новый (с нуля)", True)
        volume = st.number_input("Объём добычи, т/год (если известен)", value=500000, step=50000)
        submitted = st.form_submit_button("➡️ Создать проект")
    if submitted and name:
        S.project = {"name": name, "concept": concept, "underground": underground,
                     "open_pit": open_pit, "blasting": blasting,
                     "new_project": new_project, "volume": volume}
        S.wizard_done = True
        log_request(user_id, "wizard", json.dumps(S.project, ensure_ascii=False))
        st.success(f"Проект «{name}» создан! Концепция: {CONCEPTS[concept]}. "
                   "Переходите в «📅 График освоения» и «🗺 Дорожная карта».")
    elif S.wizard_done:
        p = S.project
        st.info(f"Текущий проект: «{p['name']}» — {CONCEPTS[p['concept']]}, "
                f"{'подземные ' if p['underground'] else ''}{'открытые ' if p['open_pit'] else ''}"
                f"работы, {p['volume']:,} т/год".replace(",", " "))
        if st.button("🔄 Начать новый проект"):
            S.wizard_done = False
            S.docs = []
            S.project = None
            st.rerun()

# ---------- ГРАФИК ОСВОЕНИЯ ----------
elif menu.startswith("📅"):
    st.header("График освоения месторождения (мастер-шаблон)")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        rows, total_dev, total = generate_schedule(S.project)
        log_request(user_id, "schedule", json.dumps({"concept": S.project["concept"],
                                                     "ops": len(rows), "months": total_dev}))
        st.success(f"Концепция: {CONCEPTS[S.project['concept']]}")
        st.markdown(f"**⏱ Ориентировочный срок до ввода в эксплуатацию: ~{total_dev} мес. "
                    f"(~{total_dev/12:.1f} года)**. Полный жизненный цикл с эксплуатацией: ~{total} мес.")
        st.caption("Длительности — базовые оценки по практике; уточняются календарным планом подрядчиков.")
        st.dataframe(rows, use_container_width=True, height=450)
        st.subheader("Загрузить график")
        fmt = st.radio("Формат", ["JSON", "CSV"])
        if fmt == "JSON":
            st.download_button("⬇ Скачать JSON", json.dumps(rows, ensure_ascii=False, indent=2),
                               file_name="schedule.json", mime="application/json")
        else:
            import csv, io as _io
            buf = _io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
            st.download_button("⬇ Скачать CSV", buf.getvalue(),
                               file_name="schedule.csv", mime="text/csv")
        with st.expander("📖 Логика зависимостей"):
            st.markdown("- Лицензия → ИРД → доразведка → запасы/ГКЗ → ТЗ+изыскания → ТЭО → ПД → ГГЭ/ГЭЭ → РД → ГКР/СМР → ПНР → ввод.\n"
                        "- Инфраструктура и ОФ идут параллельными блоками со своими экспертизами.\n"
                        "- Эксплуатация (240 мес.) и вывод из эксплуатации показаны для полного жизненного цикла, "
                        "в срок освоения не входят.")

# ---------- ДОРОЖНАЯ КАРТА ----------
elif menu.startswith("🗺"):
    st.header("Дорожная карта РП: что делать дальше")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        rows, _, _ = generate_schedule(S.project)
        log_request(user_id, "roadmap", S.project["name"])
        steps = build_roadmap(S.project, rows)
        icons = ["🔥", "📅", "🎯"]
        for (title, body), ic in zip(steps, icons):
            st.subheader(f"{ic} {title}")
            st.markdown(body)

# ---------- ДОКУМЕНТЫ ----------
elif menu.startswith("📂"):
    st.header("Шаг 2: загрузка документов проекта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект в разделе «🚀 Новый проект».")
    else:
        st.caption("Загружайте всё, что есть: ПД, ТЗ, изыскания, устав, ВОР, DWG, свой шаблон устава. "
                   "База знаний пополняется и обучается.")
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
    st.header("Чек-лист готовности проекта")
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

# ---------- АССИСТЕНТ ----------
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
        # ищем шаблон устава в загруженных документах
        template = None
        for d in S.docs:
            if "Шаблон устава" in d["types"]:
                template = d["text"]
                break
        doc = st.radio("Документ", ["Устав", "Бюджет"])
        if template:
            st.info("📎 Найден ваш шаблон устава — параметры проекта будут подставлены "
                    "(плейсхолдеры: {НАЗВАНИЕ}, {КОНЦЕПЦИЯ}, {ОБЪЕМ}, {СПОСОБ}, {ДАТА}).")
        if st.button("Сгенерировать"):
            log_request(user_id, "charter", doc)
            if doc == "Устав":
                out = gen_charter(S.project, template)
            else:
                out = gen_budget(S.project)
            st.code(out, language="text")
            st.download_button("⬇ Скачать", out, file_name=f"{doc.lower()}.txt")

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
    st.markdown(f"**Базовая** — {PRICE_BASIC} ₽/мес: мастер, график, дорожная карта, документы, чек-лист, база знаний.")
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
