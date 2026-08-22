# ============================================================
#  ГОРНЫЙ ДЕЛЬТА v5.0 «AI» — ИИ-платформа руководителя проектов
#  (горнодобывающие предприятия: открытые и подземные работы)
# ============================================================
#  ЧТО НОВОГО В v5.0:
#   • ИИ-ядро ask_ai() — GLM через OpenAI-совместимый API
#     (base_url: https://open.bigmodel.cn/api/paas/v4)
#   • 💬 Ассистент = RAG: отвечает ТОЛЬКО по вашей базе знаний,
#     с указанием источников
#   • ⚖️ NORMA AI: сверка проекта с нормативной базой
#     (ГрК РФ, 116-ФЗ, 117-ФЗ, ФНП, ПП-87 и др.) + рекомендации
#   • 📐 ИИ-чтение чертежей (vision-модель glm-4.5v):
#     DWG/DXF/PNG/JPG → распознавание и рекомендации
#   • Всё работает и без ключа — в упрощённом (правиловом) режиме
# ============================================================
#  ЗАПУСК:  pip install streamlit openai pypdf python-docx openpyxl
#            export GLM_API_KEY="ваш_ключ"
#            streamlit run app.py
#  Ключ также можно ввести в разделе «⚙️ Настройки» приложения.
# ============================================================

import streamlit as st
import json
import os
import datetime
import re
import base64

# ---------- НАСТРОЙКИ ВЛАДЕЛЬЦА ----------
OWNER_PASSWORD = "CHANGE_ME_2026"
PRICE_BASIC = 4900
PRICE_PRO = 14900
PROMO_CODES = {"PILOT2026": "pro", "DEMO": "basic"}
LOG_FILE = "users_log.jsonl"
DOCS_DIR = "knowledge"
os.makedirs(DOCS_DIR, exist_ok=True)
# ---------------------------------------------------------------

# ---------- НАСТРОЙКИ ИИ ----------
AI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
AI_MODEL_TEXT = "glm-4-plus"      # текстовая модель
AI_MODEL_VISION = "glm-4.5v"      # vision-модель для чертежей
# ---------------------------------------------------------------

st.set_page_config(page_title="Горный Дельта AI — ИИ-платформа РП", page_icon="⛏", layout="wide")

S = st.session_state
defaults = {"plan": "free", "show_owner": False, "wizard_done": False,
            "project": None, "docs": [], "api_key": os.environ.get("GLM_API_KEY", ""),
            "messages": []}
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

# ============================================================
#  ИИ-ЯДРО (GLM через OpenAI-совместимый API)
# ============================================================
def ai_enabled() -> bool:
    return bool(S.get("api_key"))

def ask_ai(prompt, system=None, temperature=0.3, max_tokens=2000):
    """Запрос к GLM. Возвращает текст ответа или None при ошибке."""
    if not ai_enabled():
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=S.api_key, base_url=AI_BASE_URL)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=AI_MODEL_TEXT, messages=msgs,
            temperature=temperature, max_tokens=max_tokens)
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Ошибка ИИ: {e}]"

def ask_ai_vision(image_b64, mime, question):
    """Запрос к vision-модели (чертежи/изображения). Возвращает текст или None."""
    if not ai_enabled():
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=S.api_key, base_url=AI_BASE_URL)
        resp = client.chat.completions.create(
            model=AI_MODEL_VISION,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                    {"type": "text", "text": question},
                ],
            }],
            temperature=0.2, max_tokens=2000)
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Ошибка ИИ (vision): {e}]"

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
        if name.endswith((".dwg", ".dxf")):
            raw = file.getvalue()
            text = raw.decode("utf-16-le", errors="ignore")
            words = re.findall(r"[А-Яа-яA-Za-z0-9 .,\-()№]{6,}", text)
            return "\n".join(words[:200]) if words else "[Чертёж: текстовые данные не извлечены]"
    except Exception as e:
        return f"[Ошибка чтения файла: {e}]"
    return "[Формат не поддерживается]"

# ============================================================
#  ОЦЕНКА СОСТАВА ОБЪЕКТОВ
# ============================================================
def estimate_assets(p):
    """Экспертная прикидка количества зданий, сооружений и оборудования."""
    vol = p.get("volume", 500000)
    big = vol >= 1_000_000
    ptype = p.get("project_type", "new")
    revamp = ptype == "revamp"
    recon = ptype == "reconstruction"
    buildings, structures, equipment = [], [], []

    if p.get("has_mine"):
        if p.get("underground"):
            buildings += [("Надшахтные здания (копры)", "2–3" if big else "1–2", ""),
                          ("АБК с банно-прачечным блоком", "1", ""),
                          ("Котельная / энергоузел", "1", "")]
            structures += [("Стволы / штольни (вскрытие)", "2–3" if big else "1–2", "главный + вспом. + вентиляционный"),
                           ("Горизонты очистных работ", "3–5" if big else "2–3", ""),
                           ("Околоствольные дворы", "1–2", ""),
                           ("Венткамеры / ГВУ", "2–3", ""),
                           ("Водоотлив: насосные камеры", "2–3", "рабочий + резервный + ремонтный"),
                           ("Отстойники шахтных вод", "1–2", "")]
            equipment += [("Подъёмные установки", "2–3" if big else "1–2", ""),
                          ("Главные вентиляторные установки", "2", "рабочая + резервная"),
                          ("Насосы главного водоотлива", "3–5", ""),
                          ("Самоходное оборудование (ПДМ, СБУ)", "6–12" if big else "3–6", ""),
                          ("Конвейерные линии", "2–4", ""),
                          ("Компрессорная станция", "1", "")]
        if p.get("open_pit"):
            buildings += [("АБК с гардеробом", "1", ""), ("Котельная / энергоузел", "1", "")]
            structures += [("Карьерные съезды / дороги", "5–10 км", ""),
                           ("Нагорные канавы / водоотведение", "1–3", ""),
                           ("Площадка перегрузки ВМ (при БВР)", "1", "или склад ВМ"),
                           ("Отвалы пустых пород", "1–2", "")]
            equipment += [("Экскаваторы", "2–4" if big else "1–2", ""),
                          ("Автосамосвалы", "6–15" if big else "3–6", ""),
                          ("Буровые станки (при БВР)", "2–3", ""),
                          ("Бульдозеры / грейдеры", "2–4", "")]
    if p.get("has_infra"):
        buildings += [("РММ / мастерские", "1–2", ""), ("Склад ГСМ", "1", ""),
                      ("Склады материалов", "1–2", ""), ("Гараж / депо", "1", "")]
        structures += [("ЛЭП / энергообъекты", "2–4", ""), ("Автодороги и площадки", "3–8 км", ""),
                       ("Водозабор и очистные", "1", ""), ("КПП, ограждение", "1 компл.", "")]
        equipment += [("Дизель-генераторы (резерв)", "1–2", "")]
    if p.get("has_plant"):
        buildings += [("Корпус крупного дробления", "1", ""), ("Корпус ср./мелкого дробления", "1", ""),
                      ("Корпус измельчения и флотации", "1", ""), ("Реагентное хозяйство", "1", "")]
        structures += [("Хвостонасосная станция", "1", ""), ("Склад концентрата", "1–2", "")]
        equipment += [("Дробилки", "2–3", ""), ("Мельницы", "2–4", ""),
                      ("Флотомашины", "1 кампания", ""), ("Конвейерные линии", "3–6", "")]
    if p.get("has_tailings"):
        structures += [("Хвостохранилище", "1", "отдельный ОПО/ГТС!"),
                       ("Насосные станции оборотного водоснабжения", "1–2", "")]
        equipment += [("Насосы пульпы и оборотной воды", "4–8", "")]
    if revamp:
        buildings = [(n, "0 (существующие)", "перевооружение") for n, _, _ in buildings]
        structures = [(n, "0 (существующие)", "") for n, _, _ in structures]
        equipment.append(("Демонтаж выводимого оборудования", "по ведомости", "отдельная позиция графика"))
    if recon:
        buildings = [(n, "частично", "часть существующих сохраняется") for n, _, _ in buildings]
    if p.get("other_scope"):
        buildings.append((f"Прочее: {p['other_scope']}", "?", "уточните на обследовании"))
    return {"Здания": buildings, "Сооружения": structures, "Оборудование": equipment}

# ============================================================
#  ГРАФИК ПРОЕКТА
# ============================================================
def get_master_template(p):
    ptype = p.get("project_type", "new")
    ops = []
    if ptype == "new":
        ops += [("LIC", "Оформление права пользования недрами", "Лицензирование", 3, []),
                ("IRD", "ИРД: лицензионные обязательства, горный отвод", "Лицензирование", 2, ["LIC"]),
                ("GR1", "Задание на доразведку, договор", "ГРР", 2, ["IRD"]),
                ("GR2", "Полевые работы доразведки", "ГРР", 8, ["GR1"]),
                ("GR3", "Подсчёт запасов, утверждение (ГКЗ)", "ГРР", 6, ["GR2"])]
        start_dep = "GR3"
    elif ptype == "reconstruction":
        ops += [("OBS", "Обследование существующих сооружений и сетей", "Подготовка", 3, []),
                ("DOK", "Сбор исходных данных предприятия", "Подготовка", 2, ["OBS"])]
        start_dep = "DOK"
    else:
        ops += [("OBS", "Экспресс-обследование оборудования", "Подготовка", 2, []),
                ("ZAD", "ТЗ на перевооружение, выбор оборудования", "Подготовка", 1, ["OBS"])]
        start_dep = "ZAD"
    if ptype in ("new", "reconstruction"):
        ops += [("TZ", "ТЗ на проектирование", "ПИР", 2, [start_dep]),
                ("IZK", "Инженерные изыскания", "ПИР", 4, [start_dep]),
                ("TEO", "ТЭО / выбор технологии", "ПИР", 3, ["TZ", "IZK"]),
                ("PI", "Проектная документация", "ПИР", 8 if ptype == "new" else 6, ["TEO"]),
                ("EXE", "Экспертиза (ГГЭ/ГЭЭ), согласования", "ПИР", 4, ["PI"]),
                ("RD", "Рабочая документация", "ПИР", 6, ["EXE"])]
        last = "RD"
    else:
        ops += [("RD", "РД на замену/модернизацию", "ПИР", 3, [start_dep]),
                ("SMR0", "Согласование «окон» и графиков вывода", "ПИР", 1, ["RD"])]
        last = "SMR0"
    if ptype == "new":
        ops += [("GKR", "Горно-капитальные работы / вскрытие", "Реализация", 12 if p.get("underground") else 8, [last]),
                ("SMR", "СМР поверхностного комплекса", "Реализация", 12, [last]),
                ("SBO", "Заказ и поставка оборудования", "Реализация", 10, [last])]
        pre = ["GKR", "SMR", "SBO"]
    elif ptype == "reconstruction":
        ops += [("SMR1", "Реконструкция по этапам при действующем производстве", "Реализация", 14, [last]),
                ("SMR2", "Переподключения к сетям, переводы", "Реализация", 3, ["SMR1"])]
        pre = ["SMR1", "SMR2"]
    else:
        ops += [("POST", "Поставка нового оборудования", "Реализация", 6, [last]),
                ("DEM", "Демонтаж выводимого оборудования (в «окна»)", "Реализация", 3, [last]),
                ("MONT", "Монтаж с минимизацией простоев", "Реализация", 5, ["POST", "DEM"])]
        pre = ["MONT"]
    ops += [("PNR", "Пусконаладочные работы", "Реализация", 3, pre),
            ("VVD", "Ввод в эксплуатацию", "Реализация", 1, ["PNR"])]
    if p.get("has_infra") and ptype == "new":
        ops += [("INF1", "ПД инфраструктуры + негосэкспертиза", "Параллельный блок", 6, ["TZ"]),
                ("INF2", "СМР инфраструктуры", "Параллельный блок", 10, ["INF1"])]
    if p.get("has_plant") and ptype == "new":
        ops += [("OF1", "ПД фабрики и хвостовго хозяйства, ГГЭ", "Параллельный блок", 10, ["TEO"]),
                ("OF2", "СМР фабрики и хвостохранилища", "Параллельный блок", 18, ["OF1"]),
                ("OF3", "ПНР фабрики", "Параллельный блок", 3, ["OF2"])]
    if p.get("blasting") and ptype == "new":
        ops += [("VPHO", "Лицензия ВПХО, решение по ВМ", "Параллельный блок", 6, ["LIC"])]
    if p.get("underground") and ptype in ("new", "reconstruction"):
        ops += [("PLA", "ПЛА, договор с ВГСЧ", "Параллельный блок", 4, [last])]
    if ptype == "new":
        ops += [("EKS", "Промышленная эксплуатация", "Эксплуатация", 240, ["VVD"]),
                ("ZAK", "Ликвидация / рекультивация", "Вывод из эксплуатации", 24, ["EKS"])]
    return ops

def generate_schedule(p):
    ops = get_master_template(p)
    vol = p.get("volume", 500000)
    scale = 1.25 if vol >= 3_000_000 else (0.85 if vol <= 200_000 else 1.0)
    dur = {o[0]: max(1, round(o[3] * scale)) for o in ops}
    deps, names, stages = {}, {}, {}
    for o in ops:
        deps[o[0]], names[o[0]], stages[o[0]] = o[4], o[1], o[2]
    start, finish = {}, {}
    def calc(oid):
        if oid in start:
            return
        start[oid] = finish[oid] = 0
        for d in deps[oid]:
            if d in dur:
                calc(d)
                start[oid] = max(start[oid], finish[d])
        finish[oid] = start[oid] + dur[oid]
    for o in ops:
        calc(o[0])
    order = sorted(ops, key=lambda o: (start[o[0]], finish[o[0]]))
    rows = [{"id": o[0], "операция": names[o[0]], "стадия": stages[o[0]],
             "старт": start[o[0]] + 1, "финиш": finish[o[0]],
             "длительность": dur[o[0]], "зависимости": ", ".join(deps[o[0]]) or "—"} for o in order]
    total = max(finish.values()) if finish else 0
    dev = max((r["финиш"] for r in rows
               if r["стадия"] not in ("Эксплуатация", "Вывод из эксплуатации")), default=0)
    return rows, dev, total

# ---------- ДОРОЖНАЯ КАРТА ----------
def build_roadmap(p):
    ptype = p.get("project_type", "new")
    if ptype == "new":
        now = ["Проверьте лицензию на недра (сроки обязательств, границы отвода).",
               "Оцените категорию запасов — при нехватке готовьте доразведку.",
               "Выберите проектировщика с СРО (реестр НОПРИЗ)."]
    elif ptype == "reconstruction":
        now = ["Закажите техобследование зданий, сетей, оборудования.",
               "Соберите исполнительную документацию.",
               "Согласуйте порядок отключений/подключений с эксплуатацией."]
    else:
        now = ["Ведомость заменяемого оборудования (что/зачем/на что).",
               "Обследование фундаментов и сетей под новое оборудование.",
               "Согласуйте «окна» с производством — простой = деньги."]
    year = ["ТЗ → изыскания/обследование → ТЭО → ПД/РД.",
            "БВР → лицензия ВПХО, решение по ВМ.",
            "Смета и бюджет — параллельно с проектированием."]
    strategy = ["💡 Инфраструктуру выносите в отдельный проект под негосэкспертизу.",
                ("ОФ и хвосты — отдельные ОПО, ГГЭ планируйте заранее." if p.get("has_plant") else ""),
                ("При перевооружении защищайте суммарный простой в графике." if ptype == "revamp" else "")]
    return [("ПРЯМО СЕЙЧАС", now), ("БЛИЖАЙШИЙ ГОД", year),
            ("СТРАТЕГИЯ", [s for s in strategy if s])]

# ============================================================
#  НОРМАТИВНАЯ БАЗА (для раздела NORMA AI)
# ============================================================
NORMA_DB = {
    "ГрК РФ (473-ФЗ)": "Градостроительный кодекс: стадии проектирования, экспертиза, разрешение на строительство.",
    "116-ФЗ": "О промышленной безопасности ОПО: регистрация ОПО, экспертиза ПБ (ГГЭ), декларация безопасности.",
    "117-ФЗ": "О безопасности ГТС: хвостохранилища, гидротехнические сооружения.",
    "Закон «О недрах» (2395-1)": "Лицензирование недропользования, горный отвод, техпроект разработки (≤24 мес. от регистрации лицензии).",
    "ПП РФ №87": "Состав разделов проектной документации.",
    "ПП РФ №2490": "Государственная экспертиза проектной документации.",
    "ФНП «Инструкции по безопасности шахт»": "Требования к подземным работам: вентиляция, водоотлив, подъём.",
    "ФНП «Правила безопасности ВМ»": "Хранение/применение ВМ, лицензия ВПХО.",
    "ФНП «Правила безопасности ГТС»": "Эксплуатация хвостохранилищ.",
    "ПУЭ / СП / ГОСТ": "Электрооборудование, СП 4.13130, строительные нормы.",
    "ФЗ-7 «Об охране окружающей среды»": "ОВОС, ПЭК, экологическая экспертиза.",
    "ФЗ-174 «Об экологической экспертизе»": "Объекты ГЭЭ, экологические требования.",
}

NORMA_SYSTEM = (
    "Ты — эксперт-нормоконтролёр в области строительства, проектирования, экологии и "
    "промышленной безопасности горнодобывающих предприятий РФ. Отвечай строго по действующему "
    "законодательству РФ, указывай конкретные НПА (номера ФЗ, ПП, ФНП, СП). Если вопрос касается "
    "объёмов/классов опасности — давай диапазоны и оговорки. Формат: краткий вывод → нормативное "
    "обоснование → рекомендация что делать. Не выдумывай номера документов."
)

def norma_offline_answer(question, project):
    """Офлайн-ответ по базе (без ИИ) — базовые правила."""
    q = question.lower()
    out = []
    if "экспертиз" in q:
        out.append("Экспертиза: ГЭЭ (ПП-2490, 117-ФЗ) для ПД; ГГЭ (116-ФЗ) для ОПО. "
                   "Хвостохранилище — экспертиза ГТС (117-ФЗ).")
    if "лиценз" in q and "впхо" in q:
        out.append("Лицензия ВПХО (119-ФЗ) — обязательна для хранения/применения ВМ. "
                   "Начинайте оформление заранее: 6+ мес.")
    if "ггэ" in q or "опо" in q:
        out.append("Регистрация ОПО в реестре Ростехнадзора (ПП-495), экспертиза ПБ — 116-ФЗ. "
                   "Шахты обычно I класса опасности.")
    if "запас" in q or "грр" in q:
        out.append("Запасы для добычи: B+C1. Утверждение ГКЗ. Техпроект — ≤24 мес. от регистрации лицензии (Закон о недрах).")
    if "эколог" in q:
        out.append("ОВОС/ПЭК — ФЗ-7; объекты ГЭЭ — ФЗ-174. Хвостохранилище и объекты на ООПТ — экпертиза.")
    if not out:
        out.append("Базовый ответ недоступен офлайн. Подключите ИИ-ключ для развёрнутой сверки с нормативкой. "
                   "Актуальная база: " + ", ".join(NORMA_DB.keys()[:6]) + ".")
    return "\n".join("• " + o for o in out)

def project_context(p):
    if not p:
        return "Проект не создан."
    tname = {"new": "новое строительство", "reconstruction": "реконструкция",
             "revamp": "техническое перевооружение"}[p.get("project_type", "new")]
    scope = [k for k, f in [("добычное предприятие", "has_mine"), ("инфраструктура", "has_infra"),
                             ("переработка (ОФ)", "has_plant"), ("хвостовое хозяйство", "has_tailings")]
             if p.get(f)]
    return (f"Параметры проекта: тип — {tname}; состав — {', '.join(scope) or '—'}; "
            f"{'подземный' if p.get('underground') else 'открытый'} способ; "
            f"{'БВР' if p.get('blasting') else 'без БВР'}; объём {p.get('volume', 0)} т/год.")

# ---------- КЛАССИФИКАЦИЯ ДОКУМЕНТОВ ----------
DOC_TYPES = {
    "Пояснительная записка / ПД": ["пояснительная записка", "пз", "проектная документация", "пд№"],
    "ТЗ / задание на проектирование": ["задание на проектирование", "тз", "техническое задание"],
    "Инженерные изыскания": ["изыскани", "геологи", "гидрогеолог", "геодез", "экологическ"],
    "Уставные документы": ["устав", "бюджет", "смет", "график", "календарн"],
    "Горно-техническая часть": ["горн", "вскрыти", "система разработк", "рудник", "шахт", "ствол", "карьер"],
    "Промышленная безопасность": ["безопасн", "фнп", "ггэ", "экспертиз", "опасный производственный", "опо"],
    "ВОР / ведомости": ["ведомост", "вор", "объём работ", "объем работ", "спецификац"],
    "Обследование / исполнительная документация": ["обследован", "исполнительн"],
    "Шаблон устава": ["устав проекта", "шаблон устава"],
}

def classify_doc(name, text):
    blob = (name + " " + text[:5000]).lower()
    found = [t for t, keys in DOC_TYPES.items() if any(k in blob for k in keys)]
    return found or ["Прочее"]

# ---------- ЧЕК-ЛИСТ ----------
REQUIRED_DOCS = [
    ("Пояснительная записка / ПД", "Закажите у проектировщика с СРО."),
    ("ТЗ / задание на проектирование", "Утвердите у заказчика."),
    ("Инженерные изыскания", "Геология/гидрогеология обязательны для подземных работ."),
    ("Горно-техническая часть", "Система разработки, вскрытие, вентиляция."),
    ("Промышленная безопасность", "Раздел ПБ, ГГЭ — обязательно для ОПО."),
    ("Уставные документы", "Устав, бюджет, график."),
    ("ВОР / ведомости", "Для контроля объёмов."),
]

def readiness_check(present, project):
    base = [(dt, "ok" if dt in present else "miss", "" if dt in present else adv)
            for dt, adv in REQUIRED_DOCS]
    if project.get("project_type") in ("reconstruction", "revamp"):
        base.append(("Обследование / исполнительная документация",
                     "ok" if "Обследование / исполнительная документация" in present else "miss",
                     "Обязательно для реконструкции/перевооружения."))
    extra = []
    if project.get("underground"):
        extra += [("Проект вентиляции / ГВУ", "miss", "Обязателен проект проветривания."),
                  ("ПЛА", "miss", "Согласуется с ВГСЧ до начала эксплуатации.")]
    if project.get("blasting"):
        extra.append(("Решение по ВМ + лицензия ВПХО", "miss", "Без ВПХО работы с ВМ невозможны."))
    if project.get("has_plant"):
        extra.append(("Проект ОФ + хвостовго хозяйства", "miss", "Отдельные ОПО/ГТС."))
    return base, extra

# ---------- ПОИСК ПО БАЗЕ ЗНАНИЙ ----------
def search_knowledge(query, top_n=4):
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

RAG_SYSTEM = (
    "Ты — ассистент руководителя горнодобывающего проекта. Отвечай ТОЛЬКО на основе "
    "предоставленных фрагментов документов пользователя. Не выдумывай факты. "
    "Если в фрагментах нет ответа — честно скажи об этом и порекомендуйте, какой документ загрузить. "
    "Указывай источник (имя файла) для каждого факта."
)

# ============================================================
#  ИНТЕРФЕЙС
# ============================================================
st.title("⛏ Горный Дельта AI")
st.caption("ИИ-платформа руководителя проектов горнодобывающего предприятия • v5.0")

user_id = st.sidebar.text_input("Ваш ID / e-mail", value="guest")

if ai_enabled():
    st.sidebar.success("🤖 ИИ подключён")
else:
    st.sidebar.warning("🤖 ИИ не подключён — упрощённый режим. Ключ: раздел «⚙️ Настройки».")

menu = st.sidebar.radio("Навигация", [
    "🚀 Новый проект (мастер)",
    "🏗 Состав объектов (оценка)",
    "📅 График проекта",
    "🗺 Дорожная карта",
    "⚖️ NORMA AI: нормативка",
    "📂 Документы проекта",
    "✅ Чек-лист готовности",
    "💬 ИИ-ассистент",
    "📋 Уставные документы",
    "📐 PRO: ИИ-анализ чертежей",
    "⚙️ Настройки",
    "💳 Подписка",
    "🔐 Кабинет владельца",
])

# ---------- МАСТЕР ----------
if menu.startswith("🚀"):
    st.header("Создание проекта")
    with st.form("wizard"):
        name = st.text_input("Название проекта", "")
        st.subheader("Тип проекта")
        ptype = st.radio("Что вы делаете?", ["new", "reconstruction", "revamp"],
                         format_func=lambda k: {"new": "🆕 Новое строительство",
                                                "reconstruction": "🏗 Реконструкция",
                                                "revamp": "⚙️ Техническое перевооружение"}[k])
        st.subheader("Что входит в проект?")
        scope = st.multiselect("Отметьте границы проекта", [
            "Добычное предприятие (рудник / карьер)",
            "Инфраструктура (АБК, ГСМ, РММ, ЛЭП, дороги)",
            "Переработка (обогатительная фабрика, ДСК)",
            "Хвостовое / шламовое хозяйство",
            "Другое (опишу сам)",
        ])
        other_scope = ""
        if "Другое (опишу сам)" in scope:
            other_scope = st.text_input("Опишите, что ещё входит")
        has_mine = "Добычное предприятие (рудник / карьер)" in scope
        has_infra = "Инфраструктура (АБК, ГСМ, РММ, ЛЭП, дороги)" in scope
        has_plant = "Переработка (обогатительная фабрика, ДСК)" in scope
        has_tailings = "Хвостовое / шламовое хозяйство" in scope
        processing = None
        if not has_plant and has_mine:
            processing = st.radio("Как перерабатывается руда?", ["own", "third", "unknown"],
                                  format_func=lambda k: {"own": "Строим свою фабрику",
                                                         "third": "Сторонний переработчик",
                                                         "unknown": "Пока не знаю"}[k])
            if processing == "own":
                has_plant = True
        c1, c2 = st.columns(2)
        with c1:
            underground = st.checkbox("Подземные горные работы")
            open_pit = st.checkbox("Открытые горные работы")
            blasting = st.checkbox("Применяются БВР", True)
        with c2:
            volume = st.number_input("Объём добычи, т/год", value=500000, step=50000)
        submitted = st.form_submit_button("➡️ Создать проект")
    if submitted and name:
        S.project = {"name": name, "project_type": ptype, "has_mine": has_mine,
                     "has_infra": has_infra, "has_plant": has_plant, "has_tailings": has_tailings,
                     "other_scope": other_scope, "processing": processing,
                     "underground": underground, "open_pit": open_pit,
                     "blasting": blasting, "volume": volume}
        S.wizard_done = True
        log_request(user_id, "wizard", json.dumps(S.project, ensure_ascii=False))
        st.success(f"Проект «{name}» создан!")
    elif S.wizard_done:
        p = S.project
        tname = {"new": "Новое строительство", "reconstruction": "Реконструкция",
                 "revamp": "Техническое перевооружение"}[p["project_type"]]
        st.info(f"Текущий проект: «{p['name']}» — {tname}, {p['volume']:,} т/год".replace(",", " "))
        if st.button("🔄 Начать новый проект"):
            S.wizard_done, S.docs, S.project = False, [], None
            st.rerun()

# ---------- СОСТАВ ОБЪЕКТОВ ----------
elif menu.startswith("🏗"):
    st.header("Оценка состава: здания, сооружения, оборудование")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        assets = estimate_assets(S.project)
        c1, c2, c3 = st.columns(3)
        c1.metric("Здания", len(assets["Здания"]))
        c2.metric("Сооружения", len(assets["Сооружения"]))
        c3.metric("Оборудование", len(assets["Оборудование"]))
        for cat, items in assets.items():
            st.subheader(cat)
            if items:
                st.table([{"Наименование": n, "Кол-во": q, "Примечание": c} for n, q, c in items])
            else:
                st.caption("— (не предусмотрено)")
        if ai_enabled() and st.button("🤖 Попросить ИИ прокомментировать состав"):
            with st.spinner("ИИ анализирует состав..."):
                out = ask_ai("Прокомментируй состав объектов проекта, укажи, что обычно "
                             "забывают предусмотреть, и риски.\n" + project_context(S.project) +
                             "\nСостав:\n" + json.dumps(assets, ensure_ascii=False)[:4000])
            if out:
                st.markdown(out)
        st.download_button("⬇ JSON", json.dumps(assets, ensure_ascii=False, indent=2),
                           file_name="assets_estimate.json")

# ---------- ГРАФИК ----------
elif menu.startswith("📅"):
    st.header("График проекта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        rows, dev, total = generate_schedule(S.project)
        if rows:
            st.success(f"⏱ До ввода: ~{dev} мес. (~{dev/12:.1f} года). Полный цикл: ~{total} мес.")
            st.dataframe(rows, use_container_width=True, height=420)
            fmt = st.radio("Скачать", ["JSON", "CSV"], horizontal=True)
            if fmt == "JSON":
                st.download_button("⬇", json.dumps(rows, ensure_ascii=False, indent=2),
                                   file_name="schedule.json")
            else:
                import csv, io as _io
                buf = _io.StringIO()
                w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)
                st.download_button("⬇", buf.getvalue(), file_name="schedule.csv")

# ---------- ДОРОЖНАЯ КАРТА ----------
elif menu.startswith("🗺"):
    st.header("Дорожная карта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        for title, items in build_roadmap(S.project):
            st.subheader(title)
            for it in items:
                st.markdown(f"• {it}")

# ---------- NORMA AI ----------
elif menu.startswith("⚖️"):
    st.header("NORMA AI: сверка с нормативной документацией")
    st.caption("ИИ отвечает по актуальному законодательству РФ: строительство, "
               "проектирование, экология, промбезопасность. База-ориентир:")
    with st.expander("📖 Нормативная база (ориентир)"):
        for k, v in NORMA_DB.items():
            st.markdown(f"**{k}** — {v}")
    q = st.text_input("Ваш вопрос по нормативке",
                      placeholder="Например: нужна ли экспертиза для реконструкции склада ВМ?")
    if st.button("⚖️ Спросить") and q.strip():
        log_request(user_id, "norma", q)
        if ai_enabled():
            with st.spinner("ИИ сверяется с нормативной базой..."):
                out = ask_ai(f"Вопрос: {q}\n\nКонтекст проекта:\n{project_context(S.project)}",
                             system=NORMA_SYSTEM)
            st.markdown(out or "[Нет ответа]")
        else:
            st.info("**Офлайн-режим (без ИИ-ключа):**")
            st.markdown(norma_offline_answer(q, S.project))
            st.caption("Для развёрнутых ответов с точными ссылками подключите ИИ в «⚙️ Настройки».")

# ---------- ДОКУМЕНТЫ ----------
elif menu.startswith("📂"):
    st.header("Загрузка документов проекта")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        files = st.file_uploader("Выберите файлы",
                                 type=["pdf", "docx", "txt", "md", "csv", "xlsx", "dwg", "dxf"],
                                 accept_multiple_files=True)
        if files:
            for f in files:
                text = extract_text(f)
                types = classify_doc(f.name, text)
                safe = f"{datetime.datetime.now():%Y%m%d%H%M%S}_{f.name}"
                try:
                    with open(os.path.join(DOCS_DIR, safe), "wb") as out:
                        out.write(f.getvalue())
                except Exception:
                    pass
                S.docs.append({"name": f.name, "text": text, "types": types})
                log_request(user_id, "upload", f.name, ",".join(types))
            st.success(f"Загружено: {len(files)} файлов.")
        if S.docs:
            st.subheader(f"В базе знаний: {len(S.docs)} документов")
            for d in S.docs:
                with st.expander(f"📄 {d['name']} — {', '.join(d['types'])}"):
                    st.text(d["text"][:1200] or "[текст не извлечён]")

# ---------- ЧЕК-ЛИСТ ----------
elif menu.startswith("✅"):
    st.header("Чек-лист готовности")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        present = set()
        for d in S.docs:
            present.update(d["types"])
        base, extra = readiness_check(present, S.project)
        ok = sum(1 for _, s, _ in base if s == "ok")
        st.progress(ok / len(base) if base else 0, f"Готовность: {ok} из {len(base)}")
        for dt, status, advice in base:
            if status == "ok":
                st.markdown(f"✅ **{dt}** — загружено")
            else:
                st.markdown(f"⚠️ **{dt}** — отсутствует → {advice}")
        for dt, status, advice in extra:
            st.markdown(f"⚠️ **{dt}** — {advice}")

# ---------- ИИ-АССИСТЕНТ ----------
elif menu.startswith("💬"):
    st.header("ИИ-ассистент по базе знаний")
    if not ai_enabled():
        st.warning("🤖 ИИ не подключён — будет показан только поиск фрагментов. "
                   "Введите ключ API в «⚙️ Настройки» для генеративных ответов.")
    if not S.docs:
        st.info("База знаний пуста. Загрузите документы в «📂 Документы проекта» — "
                "ассистент отвечает только по ВАШИМ документам.")
    else:
        for m in S.messages[-10:]:
            role = "Вы" if m["role"] == "user" else "🤖"
            st.markdown(f"**{role}:** {m['content']}")
        q = st.text_input("Вопрос", placeholder="Какая система разработки принята? Какие стволы?")
        if st.button("Спросить") and q.strip():
            log_request(user_id, "ask", q)
            results = search_knowledge(q)
            if not results:
                st.warning("Релевантных фрагментов не найдено — переформулируйте вопрос или загрузите документы.")
            else:
                context = "\n\n".join(f"[Источник: {fn}]\n{frag}" for _, fn, frag in results)
                st.markdown("**Найденные фрагменты:**")
                for _, fn, frag in results:
                    st.markdown(f"**📄 {fn}:**")
                    st.info(frag.strip()[:500])
                if ai_enabled():
                    with st.spinner("ИИ формирует ответ..."):
                        ans = ask_ai(f"Фрагменты документов:\n{context}\n\nВопрос: {q}",
                                     system=RAG_SYSTEM)
                    st.markdown("**🤖 Ответ ИИ:**")
                    st.markdown(ans or "[Нет ответа]")
                    if ans:
                        S.messages += [{"role": "user", "content": q},
                                       {"role": "assistant", "content": ans}]

# ---------- УСТАВНЫЕ ----------
elif menu.startswith("📋"):
    st.header("Уставные документы")
    if not S.wizard_done:
        st.warning("Сначала создайте проект.")
    else:
        template = next((d["text"] for d in S.docs if "Шаблон устава" in d["types"]), None)
        if template:
            st.info("📎 Найден ваш шаблон устава — параметры будут подставлены.")
        if st.button("Сгенерировать устав"):
            p = S.project
            tname = {"new": "Новое строительство", "reconstruction": "Реконструкция",
                     "revamp": "Техническое перевооружение"}[p["project_type"]]
            base = (f"УСТАВ ПРОЕКТА\n1. Название: {p['name']}\n2. Тип: {tname}\n"
                    f"3. Способ: {'подземный' if p['underground'] else 'открытый'}; "
                    f"объём ~{p['volume']:,} т/год\n".replace(",", " ")
                    + "4. Критерии успеха: сроки, бюджет ±10%, требования надзора\n")
            st.code(base, language="text")
            st.download_button("⬇ Скачать", base, file_name="charter.txt")

# ---------- ИИ-АНАЛИЗ ЧЕРТЕЖЕЙ (PRO) ----------
elif menu.startswith("📐"):
    st.header("PRO: ИИ-анализ чертежей")
    if S.plan != "pro":
        st.warning(f"🔒 Функция тарифа PRO ({PRICE_PRO} ₽/мес). Активируйте в «💳 Подписка».")
    else:
        if not ai_enabled():
            st.warning("🤖 Для ИИ-чтения чертежей введите ключ API в «⚙️ Настройки».")
        f = st.file_uploader("Загрузите чертёж", type=["dwg", "dxf", "png", "jpg", "jpeg"])
        if f:
            st.image(f) if f.name.lower().endswith((".png", ".jpg", ".jpeg")) else None
            if st.button("📐 Проанализировать чертёж (ИИ)"):
                log_request(user_id, "dwg_ai", f.name)
                if not ai_enabled():
                    st.info("**Офлайн:** извлекаем текстовые данные из файла...")
                    st.text(extract_text(f)[:1500])
                else:
                    fname = f.name.lower()
                    if fname.endswith((".png", ".jpg", ".jpeg")):
                        b64 = base64.b64encode(f.getvalue()).decode()
                        with st.spinner("ИИ читает чертёж..."):
                            ans = ask_ai_vision(b64, f"image/{'jpeg' if 'jpg' in fname else 'png'}",
                                                "Ты — инженер-проектировщик. Изучи чертёж: опиши что изображено "
                                                "(лист, штамп, спецификации, размеры), проверь ошибки и дай "
                                                "рекомендации по оптимизации (материалы, сечения, типовые решения).")
                        st.markdown("**🤖 Результат анализа:**")
                        st.markdown(ans or "[Нет ответа]")
                    else:
                        st.info("DWG/DXF — бинарный формат. Конвертируйте в PNG/JPG (скриншот или экспорт из "
                                "AutoCAD/nanoCAD) и загрузите изображение для ИИ-анализа. "
                                "Пока покажу извлечённый текст:")
                        st.text(extract_text(f)[:1500])

# ---------- НАСТРОЙКИ ----------
elif menu.startswith("⚙️"):
    st.header("Настройки ИИ")
    st.markdown("**Подключение GLM (BigModel / Z.ai)**")
    st.caption("Ключ берётся на open.bigmodel.cn → API Keys. "
               "Хранится только в текущей сессии браузера, в код не записывается.")
    key = st.text_input("API-ключ GLM", value=S.api_key, type="password",
                        placeholder="Вставьте ключ...")
    if st.button("Сохранить ключ"):
        S.api_key = key.strip()
        st.success("Ключ сохранён в сессии." if S.api_key else "Ключ очищен.")
        st.rerun()
    st.markdown("---")
    st.markdown(f"**Текущая конфигурация:**\n- Endpoint: `{AI_BASE_URL}`\n"
                f"- Текстовая модель: `{AI_MODEL_TEXT}`\n- Vision-модель: `{AI_MODEL_VISION}`")
    if ai_enabled() and st.button("🧪 Тест подключения"):
        with st.spinner("Проверка..."):
            out = ask_ai("Ответь одним словом: работает.", temperature=0.0, max_tokens=10)
        st.success(f"✅ ИИ ответил: {out}") if out and not out.startswith("[") else \
            st.error(out or "Не удалось получить ответ.")

# ---------- ПОДПИСКА ----------
elif menu.startswith("💳"):
    st.header("Подписка")
    st.markdown(f"**Базовая** — {PRICE_BASIC} ₽/мес: мастер, состав, график, чек-лист, ассистент, NORMA AI.")
    st.markdown(f"**PRO** — {PRICE_PRO} ₽/мес: + ИИ-анализ чертежей и ВОР.")
    promo = st.text_input("Промокод").strip().upper()
    if st.button("Активировать"):
        if promo in PROMO_CODES:
            S.plan = PROMO_CODES[promo]
            st.success(f"Тариф: {S.plan.upper()}")
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
                st.markdown(psych_profile(es))
                for e in es[-20:]:
                    st.text(f"[{e['ts']}] ({e['mode']}) {e['text'][:120]}")
        st.subheader("База знаний (сервер)")
        for fn in sorted(os.listdir(DOCS_DIR)):
            st.text(fn)

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 [Владелец продукта]. Все права защищены.")
