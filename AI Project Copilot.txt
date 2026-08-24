```python
# ai_project_copilot.py
# ИИ-сопровождение greenfield-проекта для Streamlit.
# Работает с уже существующим llm_assistant.py:
#   from llm_assistant import FREE_MODELS, ask_llm, build_context
#
# «Обучение» здесь реализовано корректно и безопасно:
# 1) RAG: модель отвечает по загруженным документам;
# 2) проектная память: подтвержденные пользователем факты и решения;
# 3) библиотека одобренных шаблонов/рекомендаций.
# Модели не дообучаются автоматически на закрытых данных без отдельного
# контура безопасности, согласия и MLOps-процесса.

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import streamlit as st

try:
    from llm_assistant import FREE_MODELS, ask_llm, build_context
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    FREE_MODELS = {}


# -----------------------------------------------------------------------------
# 1. Проектная память: все важные факты подтверждаются пользователем.
# -----------------------------------------------------------------------------

def init_copilot_state(S) -> None:
    defaults = {
        "copilot_messages": [],
        "copilot_facts": {},          # {key: {value, source, confidence, updated_at}}
        "copilot_wishes": [],         # пожелания РП в свободной форме
        "copilot_open_questions": [],
        "copilot_recommendations": [],
        "copilot_actions": [],
    }
    for key, value in defaults.items():
        if key not in S:
            S[key] = value


def remember_fact(S, key: str, value: str, source: str = "Подтверждено пользователем") -> None:
    if not str(value).strip():
        return
    S.copilot_facts[key] = {
        "value": str(value).strip(), "source": source,
        "confidence": "Подтверждено", "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def project_memory(S) -> str:
    facts = S.copilot_facts
    lines = []
    for key, item in facts.items():
        lines.append(f"- {key}: {item['value']} ({item['source']})")
    wishes = "\n".join(f"- {x}" for x in S.copilot_wishes[-10:]) or "—"
    return "ПОДТВЕРЖДЕННЫЕ ФАКТЫ ПРОЕКТА:\n" + ("\n".join(lines) or "—") + \
           "\n\nПОЖЕЛАНИЯ РУКОВОДИТЕЛЯ ПРОЕКТА:\n" + wishes


# -----------------------------------------------------------------------------
# 2. Дерево наводящих вопросов. Логика работает даже без LLM.
# -----------------------------------------------------------------------------

QUESTION_BANK = [
    {"id": "project_goal", "topic": "Цель", "question": "Какой измеримый результат должен быть достигнут проектом и к какой дате?", "required": True},
    {"id": "license", "topic": "Недра", "question": "Есть ли лицензия на недра? Укажите номер, недропользователя, срок действия и ключевые лицензионные условия либо загрузите лицензию.", "required": True},
    {"id": "reserves", "topic": "Недра", "question": "Какой документ подтверждает запасы: протокол ГКЗ/ТКЗ, дата состояния запасов, категории и проектная производительность?", "required": True},
    {"id": "method", "topic": "Технология", "question": "Какой способ разработки и предмет текущего этапа: разведка, вскрытие, добыча, инфраструктура, переработка?", "required": True},
    {"id": "boundaries", "topic": "Границы", "question": "Какие объекты входят в текущий этап, а какие сознательно исключены или вынесены в отдельные проекты?", "required": True},
    {"id": "target_date", "topic": "Сроки", "question": "Какая дата является непереносимой: начало ГКР/СМР, первая руда, ввод объекта, лицензионный срок?", "required": True},
    {"id": "ird", "topic": "ИРД", "question": "Какие ИРД и изыскания уже готовы, кто владелец отсутствующих данных и когда они будут переданы?", "required": True},
    {"id": "design_route", "topic": "Проектирование", "question": "Какой пакет нужен на этом этапе: ТП, ПД по №87, РД, локальные проекты? Назначен ли ГИП/генпроектировщик?", "required": True},
    {"id": "expertise", "topic": "Экспертизы", "question": "Какие маршруты экспертиз и согласований уже подтверждены: ЦКР, ГГЭ/НГЭ, ГЭЭ, ОПО, ГТС, КЭР, разрешения?", "required": True},
    {"id": "dependencies", "topic": "Зависимости", "question": "Какие объекты должны быть готовы до старта основных горных работ: ВП, РММ, ЛЭП/ДЭС, дороги, водоотлив, вентиляция, связь, ВМ?", "required": True},
    {"id": "budget", "topic": "Финансы", "question": "Каков лимит CAPEX/OPEX, распределение по годам, резерв и процедура согласования изменений?", "required": True},
    {"id": "risks", "topic": "Риски", "question": "Назовите три главных риска проекта и ранние признаки их наступления.", "required": True},
]


def unanswered_questions(S) -> list[dict[str, str]]:
    return [q for q in QUESTION_BANK if q["id"] not in S.copilot_facts]


def next_guiding_question(S, greenfield_project: dict[str, Any] | None = None) -> dict[str, str] | None:
    remaining = unanswered_questions(S)
    if not remaining:
        return None

    # Контекстные вопросы подземного объекта получают приоритет после базовых.
    p = greenfield_project or {}
    if p.get("mine_method") == "подземный" and "method" in S.copilot_facts:
        special = [
            ("ventilation", "Подземные работы", "Как будет обеспечено проветривание: ГВУ, выработки, этап ввода, исходные данные для VentSim?"),
            ("dewatering", "Подземные работы", "Как предусмотрены шахтный водоотлив, отстойник/очистка и отведение воды?"),
            ("explosives", "Подземные работы", "Как организуется снабжение ВМ: подрядчик, площадка перегрузки или склад; какие границы включаются в проект?"),
        ]
        for qid, topic, question in special:
            if qid not in S.copilot_facts:
                return {"id": qid, "topic": topic, "question": question, "required": True}
    return remaining[0]


def fallback_reply(S, user_text: str, greenfield_project: dict[str, Any] | None) -> dict[str, Any]:
    """Предсказуемый ответ без внешней модели: вопрос + первичная рекомендация."""
    q = next_guiding_question(S, greenfield_project)
    recommendations = []
    lower = user_text.lower()
    if any(x in lower for x in ["срок", "дедлайн", "опоздан", "задерж"]):
        recommendations.append("Зафиксируйте целевую дату как контрольную веху и назначьте владельцев критических ИРД.")
    if any(x in lower for x in ["подзем", "шахт", "рудник"]):
        recommendations.append("Для подземного контура отдельно проверьте вентиляцию, водоотлив, ВМ, ОПО и готовность инфраструктуры до начала проходки.")
    if any(x in lower for x in ["тз", "задани"]):
        recommendations.append("Перед выпуском ТЗ подтвердите предмет, границы этапа, исходные данные, специальные разделы, форматы выдачи и маршрут экспертиз.")
    return {
        "answer": "Я зафиксировал запрос. " + (" ".join(recommendations) if recommendations else "Для точной рекомендации уточню следующий критичный факт проекта."),
        "question": q["question"] if q else "Базовая диагностика завершена. Опишите, какой документ или управленческое решение нужно подготовить.",
        "facts": [], "actions": [], "recommendations": recommendations,
    }


# -----------------------------------------------------------------------------
# 3. LLM-оркестратор. Модель обязана возвращать JSON, но имеет fallback.
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — AI Project Copilot для greenfield-проектов добычи полезных ископаемых в России.
Твоя цель — помогать руководителю проекта структурировать входные данные, дорожную карту, ТЗ, реестр ИРД, риски и документы.

Правила:
1. Не выдумывай реквизиты, нормы, даты, лицензии, статусы экспертиз или проектные решения.
2. Разделяй: подтверждено документом; сообщил пользователь; предположение; требуется экспертная проверка.
3. Не называй применимость экспертизы окончательной без оговорки «проверить применимость профильным экспертом».
4. Задавай ровно ОДИН следующий вопрос, самый важный для снижения риска или построения дорожной карты.
5. Учитывай пожелания руководителя, но выявляй конфликт пожеланий со сроком, бюджетом, безопасностью и разрешительной частью.
6. Ответ должен быть практичным: краткий вывод, 1–3 действия, один вопрос.
7. Возвращай ТОЛЬКО корректный JSON без markdown:
{
  "answer":"...",
  "question":"...",
  "facts":[{"key":"...","value":"...","source":"сообщил пользователь|из документа, требует подтверждения"}],
  "actions":[{"title":"...","owner":"...","due_hint":"...","priority":"high|medium|low"}],
  "recommendations":["..."]
}
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def ai_reply(api_key: str, model_name: str, user_text: str, S, search_results: list[tuple], greenfield_project: dict[str, Any] | None) -> dict[str, Any]:
    """Вызывает LLM только при наличии ключа; иначе безопасный fallback."""
    if not (LLM_AVAILABLE and api_key and model_name in FREE_MODELS):
        return fallback_reply(S, user_text, greenfield_project)

    evidence = build_context(search_results) if search_results else "В загруженных документах релевантные фрагменты не найдены."
    next_q = next_guiding_question(S, greenfield_project)
    user_prompt = f"""{SYSTEM_PROMPT}

{project_memory(S)}

ПРОФИЛЬ ПРОЕКТА ИЗ МАСТЕРА:
{json.dumps(greenfield_project or {}, ensure_ascii=False, default=str)}

ФРАГМЕНТЫ ЗАГРУЖЕННЫХ ДОКУМЕНТОВ:
{evidence[:12000]}

СЛЕДУЮЩИЙ ДЕТЕРМИНИРОВАННЫЙ ВОПРОС, ЕСЛИ ДАННЫХ НЕДОСТАТОЧНО:
{next_q['question'] if next_q else 'Соберите пожелания к результату.'}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{user_text}
"""
    raw = ask_llm(api_key, user_prompt, "", FREE_MODELS[model_name])
    parsed = _extract_json(raw)
    if not parsed:
        return {"answer": raw, "question": next_q["question"] if next_q else "Что подготовить следующим шагом?",
                "facts": [], "actions": [], "recommendations": []}
    return parsed


def apply_ai_result(S, result: dict[str, Any]) -> None:
    """Автосохранение только с пометкой 'требует подтверждения'."""
    for fact in result.get("facts", []):
        key, value = fact.get("key", ""), fact.get("value", "")
        if key and value:
            S.copilot_facts[key] = {
                "value": value, "source": fact.get("source", "AI-извлечение, требует подтверждения"),
                "confidence": "Требует подтверждения", "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
    S.copilot_actions.extend(result.get("actions", []))
    S.copilot_recommendations.extend(result.get("recommendations", []))


# -----------------------------------------------------------------------------
# 4. UI: чат + память + подтверждение фактов + пользовательские пожелания.
# -----------------------------------------------------------------------------

def render_ai_copilot(S, docs: list[dict], search_fn, greenfield_project: dict[str, Any] | None = None) -> None:
    init_copilot_state(S)
    st.header("🤖 AI Project Copilot")
    st.caption("Диалоговый помощник по документам, дорожной карте и ТЗ. Он не заменяет ГИП, эколога, маркшейдера, юриста или экспертизу.")

    with st.expander("Как работает проектная память", expanded=False):
        st.write("Ассистент использует загруженные документы, ответы в диалоге и подтвержденные факты. Любой факт, извлеченный ИИ, помечается как требующий подтверждения.")
        wish = st.text_area("Ваши пожелания к проекту и работе ассистента", placeholder="Например: ввод первой очереди не позднее IV квартала 2028; инфраструктуру вести отдельными титулами; бюджет показывать в тыс. руб.")
        if st.button("Сохранить пожелания") and wish.strip():
            S.copilot_wishes.append(wish.strip())
            st.success("Пожелание сохранено в проектной памяти.")

    # Настройки совместимы с текущим app.py.
    api_key, model_name = "", ""
    with st.expander("⚙️ Настройки ИИ", expanded=False):
        if LLM_AVAILABLE:
            api_key = st.text_input("API-ключ OpenRouter", value=S.get("api_key", ""), type="password", key="copilot_api_key")
            model_name = st.selectbox("Модель", list(FREE_MODELS.keys()), key="copilot_model")
            S.api_key, S.model_name = api_key, model_name
        else:
            st.warning("Не найден llm_assistant.py. Доступен детерминированный режим наводящих вопросов и проектной памяти.")

    tabs = st.tabs(["💬 Диалог", "🧠 Факты проекта", "✅ Действия и рекомендации"])
    with tabs[0]:
        for msg in S.copilot_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        question = next_guiding_question(S, greenfield_project)
        if not S.copilot_messages and question:
            with st.chat_message("assistant"):
                st.markdown("Начнем с самого важного для управляемого запуска проекта.")
                st.markdown(f"**{question['question']}**")

        prompt = st.chat_input("Напишите ответ, пожелание или задачу: «сформируй ТЗ на ПД вскрытия»")
        if prompt:
            S.copilot_messages.append({"role": "user", "content": prompt})
            results = search_fn(prompt) if docs else []
            with st.spinner("AI Project Copilot анализирует контекст проекта..."):
                result = ai_reply(api_key, model_name, prompt, S, results, greenfield_project)
            apply_ai_result(S, result)
            answer = result.get("answer", "")
            next_question = result.get("question", "")
            content = answer + (f"\n\n**Следующий вопрос:** {next_question}" if next_question else "")
            S.copilot_messages.append({"role": "assistant", "content": content})
            st.rerun()

    with tabs[1]:
        st.subheader("Подтверждаемые факты")
        if not S.copilot_facts:
            st.info("Фактов пока нет. Ответьте на первый вопрос или загрузите документы.")
        for key, item in list(S.copilot_facts.items()):
            a, b = st.columns([5, 1])
            with a:
                st.markdown(f"**{key}**: {item['value']}")
                st.caption(f"{item['confidence']} · {item['source']} · {item['updated_at']}")
            with b:
                if item["confidence"] != "Подтверждено" and st.button("Подтвердить", key=f"confirm_{key}"):
                    item["confidence"] = "Подтверждено"
                    item["source"] = "Подтверждено пользователем"
                    st.rerun()

    with tabs[2]:
        st.subheader("Предложенные действия")
        if not S.copilot_actions:
            st.info("ИИ будет добавлять действия после ваших ответов.")
        for action in S.copilot_actions[-20:]:
            priority = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(action.get("priority"), "🔵")
            st.markdown(f"{priority} **{action.get('title', 'Действие')}** · {action.get('owner', 'владелец не назначен')}")
            if action.get("due_hint"): st.caption(f"Срок: {action['due_hint']}")
        st.subheader("Рекомендации")
        for recommendation in dict.fromkeys(S.copilot_recommendations[-20:]):
            st.markdown(f"- {recommendation}")
```

```python
# ИНТЕГРАЦИЯ В app.py
#
# 1. После импортов:
from ai_project_copilot import render_ai_copilot

# 2. Добавьте в меню sidebar:
# "🤖 AI Project Copilot",
#
# 3. Добавьте отдельную ветку интерфейса:
elif menu.startswith("🤖"):
    # Если Greenfield Command Center подключен, передайте его профиль проекта.
    greenfield_profile = S.get("gf_project", {})
    render_ai_copilot(S, S.docs, search_knowledge, greenfield_profile)

# 4. В requirements.txt уже достаточно зависимостей вашего проекта.
# Для LLM нужен существующий llm_assistant.py и API-ключ OpenRouter.
```

```python
# РЕКОМЕНДУЕМОЕ ДОПОЛНЕНИЕ В llm_assistant.py
# Убедитесь, что ask_llm надежно возвращает строку и обрабатывает ошибки сети:

def ask_llm(api_key, prompt, context, model):
    try:
        # ваш запрос к OpenRouter; prompt уже включает контекст в AI Copilot
        ...
    except Exception as exc:
        return f"Не удалось получить ответ ИИ: {exc}. Проверьте ключ, модель и соединение."
```
