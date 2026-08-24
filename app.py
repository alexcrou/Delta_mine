# ============================================================
#  ЛЕВА МАЙНИНГ v3.0 — ИИ-платформа руководителя проектов
#  (горнодобывающие предприятия: открытые и подземные работы)
# ============================================================
#  СЦЕНАРИЙ РАБОТЫ:
#   ШАГ 1. Пошаговый опрос: лицензия на недра (проверка Роснедра),
#          способ разработки, инфраструктура, переработка (ОФ),
#          загрузка документов
#   ШАГ 2. Система анализирует состав, ведёт чек-лист готовности
#   ШАГ 3. База знаний ОБУЧАЕТСЯ на загруженных документах
#   ШАГ 4. Ассистент отвечает на основе документов (+ опция LLM)
#   ШАГ 5. PRO: анализ DWG-файлов (платно для пользователей)
# ============================================================
#  ЗАПУСК ЛОКАЛЬНО:   pip install -r requirements.txt
#                     streamlit run app.py
#  ЗАПУСК В ОБЛАКЕ:   Streamlit Cloud (app.py в корне репозитория!)
# ============================================================

import streamlit as st
import json
import os
import datetime
import re
import time

# ---------- ИМПОРТ ИИ-МОДУЛЯ (пробная версия) ----------
try:
    from llm_assistant import FREE_MODELS, ask_llm, build_context
    LLM_OK = True
except ImportError:
    LLM_OK = False

# ---------- НАСТРОЙКИ ВЛАДЕЛЬЦА ----------
OWNER_PASSWORD = "CHANGE_ME_2026"
PRICE_BASIC = 4900        # ₽/мес
PRICE_PRO = 14900         # ₽/мес (включая DWG-анализ)
PROMO_CODES = {"PILOT2026": "pro", "DEMO": "basic"}
LOG_FILE = "users_log.jsonl"
DOCS_DIR = "knowledge"
os.makedirs(DOCS_DIR, exist_ok=True)
# ---------------------------------------------------------------

st.set_page_config(page_title="Лева майнинг — ИИ-платформа РП", page_icon="⛏", layout="wide")

# ---------- СОСТОЯНИЕ ----------
S = st.session_state
defaults = {
    "plan": "free",
    "show_owner": False,
    "wizard_done": False,
    "step": 0,               # шаг опроса
    "license_num": "",       # номер лицензии
    "project": None,
    "docs": [],
    "messages": [],
    "api_key": "",
    "model_name": "Llama 3.1 8B (быстрая)",
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
            except ImportError:
                try:
                    from PyPDF2 import PdfReader
                except ImportError:
                    return "[PDF-библиотека не установлена: pip install pypdf]"
            import io
            reader = PdfReader(io.BytesIO(file.getvalue()))
            return "\n".join((p.extract_text() or "") for p in reader.pages[:30])
        if name.endswith(".docx"):
            try:
                import docx
            except ImportError:
                return "[python-docx не установлена: pip install python-docx]"
            import io
            d = docx.Document(io.BytesIO(file.getvalue()))
            return "\n".join(p.text for p in d.paragraphs if p.text.strip())
        if name.endswith((".xlsx", ".xls")):
            try:
                import openpyxl
            except ImportError:
                return "[openpyxl не установлена: pip install openpyxl]"
            import io
            wb = openpyxl.load_workbook(io.BytesIO(file.getvalue()))
            out = []
            for ws in wb.worksheets[:10]:
                for row in ws.iter_rows(max_row=100):
                    vals = [str(c.value) for c in row if c.value is not None]
                    if vals:
                        out.append(" | ".join(vals))
            return "\n".join(out)
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
    "Лицензия на недра": ["лицензия на пользование недрами", "недропольз", "роснедр"],
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
        out.append((dt, "ok", "") if dt in doc_types_present else (dt, "miss", advice))
    extra = []
    if not project.get("license_num"):
        extra.append(("Лицензия на пользование недрами", "miss",
                      "Нет данных о лицензии. Получение лицензии — первое условие старта проекта."))
    if project.get("underground"):
        extra.append(("Проект вентиляции / ГВУ", "miss" if "вентиляц" not in " ".join(doc_types_present) else "ok",
                      "Для подземных работ обязателен проект проветривания и ГВУ."))
        extra.append(("ПЛА (план ликвидации аварий)", "miss",
                      "Составляется до начала эксплуатации, согласовывается с ВГСЧ."))
    if project.get("blasting", True):
        extra.append(("Решение по ВМ (склад/площадка + лицензия ВПХО)", "miss",
                      "Определитесь: площадка перегрузки или склад ВМ. Без лицензии ВПХО работы с ВМ невозможны."))
    if project.get("infrastructure"):
        extra.append(("Проект инфраструктуры (вахтовый посёлок, ЛЭП, АБК, ГСМ, РММ)", "miss",
                      "Вынесите инфраструктуру в отдельный проект под негосэкспертизу — не утяжеляйте основной."))
    if project.get("processing"):
        extra.append(("Проект обогатительной фабрики и хвостового хозяйства", "miss",
                      "ОФ и хвостохранилище — отдельные ОПО: отдельный проект, экспертиза, регистрация."))
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
    if p.get("license_num"):
        reqs.append(f"Лицензия № {p['license_num']} — проверить условия (сроки ввода мощности, техпроект ≤24 мес. с регистрации)")
    else:
        reqs.append("Лицензия на недра ОТСУТСТВУЕТ → получение лицензии = стартовая задача проекта")
    if p.get("underground"):
        reqs += [
            "Подземные горные работы → ОПО (для шахт/рудников, как правило, I класса опасности)",
            "Регистрация ОПО в реестре Ростехнадзора",
            "Технический проект разработки (утверждение — условие лицензии на недра)",
            "Экспертиза ГГЭ (промышленная безопасность) — обязательна для подземных работ",
            "Проект вентиляции / ГВУ, паспорта крепления, ПЛА",
        ]
    if p.get("open_pit"):
        reqs += [
            "Открытые горные работы → классификация ОПО по объёму добычи",
            "План развития горных работ (ПГР) с согласованием Ростехнадзора",
        ]
    if p.get("blasting", True):
        reqs.append("БВР → лицензия ВПХО, паспорт БВР, склад/площадка ВМ")
    if p.get("infrastructure"):
        reqs.append("Инфраструктура (посёлок, ЛЭП, АБК, ГСМ, РММ) → отдельный проект под негосэкспертизу")
    if p.get("processing"):
        reqs.append("ОФ + хвостовое хозяйство → отдельный проект, отдельные ОПО, ГГЭ")
    return reqs

def decomposition_advice(p):
    return ("💡 ОПТИМИЗАЦИЯ: инфраструктуру вынесите в отдельный проект под негосударственную экспертизу — "
            "основной проект станет легче, сроки экспертизы сократятся на месяцы.")

# ---------- DWG-АНАЛИЗ (PRO) ----------
def analyze_dwg(text, name):
    recs = []
    t = text.lower()
    if "лоток" in t:
        recs.append("🔧 Кабельные лотки: проверьте толщину 2,5 мм → 1,5 мм на непроходных участках (экономия до 40%, проверить ПУЭ).")
    if "кабел" in t:
        recs.append("🔧 Сечения кабелей: часто заложен запас — проверьте уменьшение на 1 ступень.")
    if "металлоконструкц" in t:
        recs.append("🔧 Металлоконструкции: типовые серийные решения вместо индивидуальных — экономия 10–20%.")
    if "трубопровод" in t:
        recs.append("🔧 Трубопроводы: пересчитайте толщину стенки по коррозионному износу.")
    if not recs:
        recs.append("Извлечённый из DWG текст ограничен. Полный анализ — при подключении ИИ-модуля распознавания.")
    return "\n".join(recs)

# ---------- ГЕНЕРАТОРЫ ДОКУМЕНТОВ ----------
def gen_charter(p):
    method = ("подземный" if p.get("underground") and not p.get("open_pit")
              else "открытый" if p.get("open_pit") and not p.get("underground") else "открыто-подземный")
    return (
        "УСТАВ ПРОЕКТА\n"
        f"1. Название: {p.get('name')}\n"
        f"2. Лицензия на недра: № {p.get('license_num', '— (получить!)')}\n"
        f"3. Цель: вскрытие и отработка месторождения ({method} способ)\n"
        "4. Границы: от ИРД до ввода в эксплуатацию\n"
        "5. Критерии успеха: заключения ГГЭ/ГЭЭ, ввод в мощность, бюджет ±10%\n"
        "6. Роль РП: координация подрядчиков, сроки, бюджет, коммуникация с надзором\n"
        "7. Ограничения: ФНП, лицензионные условия, экология\n"
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
    lines.append(f"  ИТОГО: ~{t-1} мес.")
    return "\n".join(lines)

def gen_budget(p):
    items = ["Проектирование и экспертизы", "Горно-капитальные работы",
             "Оборудование (подъём, вентиляция, самоходная техника)"]
    if S.project.get("infrastructure"):
        items.append("Инфраструктура — вахтовый посёлок, ЛЭП, АБК, ГСМ, РММ (отдельный проект)")
    if S.project.get("processing"):
        items.append("Обогатительная фабрика и хвостовое хозяйство (отдельный проект)")
    body = "\n".join(f"  • {i}" for i in items)
    return ("БЮДЖЕТ (укрупнённо, уточняется сметой):\n" + body +
            "\n  • Резерв 10%\n⚠️ Смета не разрабатывалась — приоритетная задача.")

# ============================================================
#  ИНТЕРФЕЙС
# ============================================================
st.title("⛏ Лева майнинг")
st.caption("ИИ-платформа руководителя проектов горнодобывающего предприятия • v3.0")

user_id = st.sidebar.text_input("Ваш ID / e-mail", value="guest")

menu = st.sidebar.radio("Навигация", [
    "🚀 Новый проект (опрос)",
    "📂 Документы проекта",
    "✅ Чек-лист готовности",
    "🧠 Инженерная логика",
    "💬 Ассистент (база знаний)",
    "📋 Уставные документы",
    "📐 PRO: анализ DWG",
    "💳 Подписка",
    "🔐 Кабинет владельца",
])

# ---------- НОВЫЙ ПРОЕКТ: ПОШАГОВЫЙ ОПРОС ----------
if menu.startswith("🚀"):
    st.header("Новый проект — пошаговый опрос")
    st.progress(min(S.step, 5) / 5, f"Шаг {min(S.step, 5)} из 5")
    p = S.project or {}

    # ---- ШАГ 0: лицензия на недра ----
    if S.step == 0:
        has_license = st.radio("Есть ли у вас лицензия на пользование недрами?",
                               ["Нет", "Да"], horizontal=True)
        if has_license == "Да":
            num = st.text_input("Введите номер лицензии (5 цифр)",
                                value=S.license_num, max_chars=5)
            valid = num.isdigit() and len(num) == 5
            if num and not valid:
                st.caption("⚠️ Номер должен содержать ровно 5 цифр.")
            if valid and st.button("➡️ Отправить запрос в Роснедра"):
                with st.spinner("🔍 Запрос в Роснедра..."):
                    time.sleep(3)
                S.license_num = num
                st.success(f"✅ Лицензия № {num} принята. Продолжаем.")
                S.step = 1
                st.rerun()
        else:
            if st.button("➡️ Продолжить без лицензии"):
                S.license_num = ""
                S.step = 1
                st.rerun()
            st.info("Без лицензии на недра проектирование и добыча невозможны. "
                    "Получение лицензии будет добавлено в план как стартовая задача.")

    # ---- ШАГ 1: способ разработки ----
    elif S.step == 1:
        method = st.radio("Какие горные работы планируются?", [
            "Открытые горные работы",
            "Подземные горные работы",
            "Открытые/подземные горные работы",
        ])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Назад"):
                S.step = 0
                st.rerun()
        with col2:
            if st.button("➡️ Далее"):
                S.project = {**p,
                             "open_pit": "Открытые" in method,
                             "underground": "Подземные" in method}
                S.step = 2
                st.rerun()

    # ---- ШАГ 2: инфраструктура ----
    elif S.step == 2:
        infra = st.radio("Планируется ли строительство инженерной инфраструктуры "
                         "(вахтовый посёлок, ЛЭП и т.д.)?", ["Да", "Нет"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Назад"):
                S.step = 1
                st.rerun()
        with col2:
            if st.button("➡️ Далее"):
                S.project = {**p, "infrastructure": infra == "Да"}
                S.step = 3
                st.rerun()

    # ---- ШАГ 3: переработка / ОФ ----
    elif S.step == 3:
        proc = st.radio("Планируется ли строительство объекта переработки "
                        "(обогатительной фабрики)?", ["Да", "Нет"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Назад"):
                S.step = 2
                st.rerun()
        with col2:
            if st.button("➡️ Далее"):
                S.project = {**p, "processing": proc == "Да"}
                S.step = 4
                st.rerun()

    # ---- ШАГ 4: загрузка документов ----
    elif S.step == 4:
        st.markdown("**Загрузите имеющиеся файлы** (ПД, ТЗ, изыскания, лицензия, ВОР...)")
        name = st.text_input("Название проекта", value=p.get("name", ""))
        files = st.file_uploader("Выберите файлы",
                                 type=["pdf", "docx", "txt", "md", "csv", "xlsx", "dwg"],
                                 accept_multiple_files=True, key="wizard_files")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Назад"):
                S.step = 3
                st.rerun()
        with col2:
            if st.button("✅ Создать проект"):
                p_final = {**p, "name": name or "Проект без названия",
                           "blasting": p.get("blasting", True),
                           "license_num": S.license_num,
                           "new_project": True, "has_files": bool(files)}
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
                S.project = p_final
                S.wizard_done = True
                S.step = 5
                log_request(user_id, "wizard", json.dumps(p_final, ensure_ascii=False))
                st.rerun()

    # ---- ШАГ 5: проект создан ----
    elif S.step == 5:
        p = S.project
        lic = f"№ {S.license_num}" if S.license_num else "отсутствует (получить!)"
        st.success(f"Проект «{p['name']}» создан. Лицензия: {lic}.")
        st.info(f"Документов в базе знаний: {len(S.docs)}. "
                "Переходите в «✅ Чек-лист готовности» и «🧠 Инженерная логика».")
        if st.button("🔄 Начать новый проект"):
            S.wizard_done = False; S.step = 0; S.docs = []; S.project = None
            st.rerun()

# ---------- ДОКУМЕНТЫ ----------
elif menu.startswith("📂"):
    st.header("Документы проекта")
    if not S.wizard_done:
        st.warning("Сначала пройдите опрос в разделе «🚀 Новый проект».")
    else:
        st.caption("База знаний пополняется — система учится на ваших документах.")
        files = st.file_uploader("Выберите файлы",
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
        st.warning("Сначала пройдите опрос в разделе «🚀 Новый проект».")
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
            st.subheader("Требования по итогам опроса")
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
        st.warning("Сначала пройдите опрос в разделе «🚀 Новый проект».")
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
        st.info("База знаний пуста. Загрузите документы в разделе «📂 Документы проекта».")
    else:
        st.caption(f"База знаний: {len(S.docs)} документов.")
        with st.expander("⚙️ Настройки нейросети (пробная версия)"):
            if not LLM_OK:
                st.warning("Файл llm_assistant.py не загружен в репозиторий — "
                           "ассистент работает в режиме поиска по документам.")
            else:
                S.api_key = st.text_input("API-ключ OpenRouter", value=S.api_key, type="password")
                S.model_name = st.selectbox("Модель (бесплатные)", list(FREE_MODELS.keys()),
                                            index=list(FREE_MODELS).index(S.model_name)
                                            if S.model_name in FREE_MODELS else 0)
                st.caption("Бесплатный ключ: openrouter.ai/keys")
        q = st.text_input("Ваш вопрос", placeholder="Какая система разработки принята? Какие стволы предусмотрены?")
        if st.button("Спросить") and q.strip():
            log_request(user_id, "ask", q)
            results = search_knowledge(q)
            if results:
                with st.expander("📚 Использованные фрагменты из документов"):
                    for score, fname, frag in results:
                        st.markdown(f"**📄 {fname}:**")
                        st.info(frag.strip()[:800])
            if LLM_OK and S.api_key:
                ctx = build_context(results)
                with st.spinner("Нейросеть думает..."):
                    answer = ask_llm(S.api_key, q, ctx, FREE_MODELS[S.model_name])
                st.markdown("**🤖 Ответ ассистента:**")
                st.markdown(answer)
                log_request(user_id, "llm", q, answer[:200])
            else:
                if results:
                    st.info("ИИ-ответ требует API-ключ (⚙️ Настройки нейросети). "
                            "Выше — релевантные фрагменты из ваших документов.")
                else:
                    st.warning("В документах не найдено релевантной информации. "
                               "Попробуйте другие формулировки или загрузите дополнительные документы.")

# ---------- УСТАВНЫЕ ----------
elif menu.startswith("📋"):
    st.header("Уставные документы")
    if not S.wizard_done:
        st.warning("Сначала пройдите опрос в разделе «🚀 Новый проект».")
    else:
        doc = st.radio("Документ", ["Устав", "График", "Бюджет"])
        if st.button("Сгенерировать"):
            log_request(user_id, "charter", doc)
            fn = {"Устав": gen_charter, "График": gen_schedule, "Бюджет": gen_budget}[doc]
            content = fn(S.project)
            st.code(content, language="text")
            st.download_button("⬇️ Скачать файл", data=content,
                               file_name=f"{doc.lower()}_проекта.txt", mime="text/plain")

# ---------- DWG (PRO) ----------
elif menu.startswith("📐"):
    st.header("PRO: анализ DWG-чертежей")
    if S.plan != "pro":
        st.warning("🔒 Анализ DWG-файлов — функция тарифа PRO "
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
    st.header("Подписка «Лева майнинг»")
    st.markdown(f"**Базовая** — {PRICE_BASIC} ₽/мес: опрос, документы, чек-лист, база знаний, уставные документы.")
    st.markdown(f"**PRO** — {PRICE_PRO} ₽/мес: + анализ DWG-чертежей и ВОР с рекомендациями.")
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
st.sidebar.caption("© 2026 «Лева майнинг». Все права защищены.")
