# ai_project_copilot.py
# Python 3.9+ / Streamlit Cloud compatible.
# ВАЖНО: при сохранении в .py НЕ копируйте строки ```python и ```.

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

try:
    from llm_assistant import FREE_MODELS, ask_llm, build_context
    LLM_AVAILABLE = True
except ImportError:
    FREE_MODELS = {}
    LLM_AVAILABLE = False


QUESTION_BANK = [
    {"id": "project_goal", "topic": "Цель", "question": "Какой измеримый результат должен быть достигнут проектом и к какой дате?"},
    {"id": "license", "topic": "Недра", "question": "Есть ли лицензия на недра? Укажите номер, недропользователя, срок действия и ключевые лицензионные условия либо загрузите лицензию."},
    {"id": "reserves", "topic": "Недра", "question": "Каким документом подтверждены запасы: протокол ГКЗ/ТКЗ, дата состояния запасов, категории и проектная производительность?"},
    {"id": "method", "topic": "Технология", "question": "Какой способ разработки и предмет текущего этапа: разведка, вскрытие, добыча, инфраструктура, переработка?"},
    {"id": "boundaries", "topic": "Границы", "question": "Какие объекты входят в текущий этап, а какие вынесены в отдельные проекты?"},
    {"id": "target_date", "topic": "Сроки", "question": "Какая дата является непереносимой: начало ГКР/СМР, первая руда, ввод объекта или лицензионный срок?"},
    {"id": "ird", "topic": "ИРД", "question": "Какие ИРД и изыскания готовы, кто владелец отсутствующих данных и когда они будут переданы?"},
    {"id": "design_route", "topic": "Проектирование", "question": "Какой пакет требуется: ТП, ПД по ПП РФ №87, РД, локальные проекты? Назначен ли ГИП/генпроектировщик?"},
    {"id": "expertise", "topic": "Экспертизы", "question": "Какие маршруты экспертиз и согласований подтверждены: ЦКР, ГЭЭ, государственная/негосударственная экспертиза, ОПО, ГТС?"},
    {"id": "dependencies", "topic": "Зависимости", "question": "Какие объекты должны быть готовы до старта горных работ: ВП, РММ, ЛЭП/ДЭС, водоотлив, вентиляция, связь, ВМ?"},
    {"id": "budget", "topic": "Финансы", "question": "Каков лимит CAPEX/OPEX, распределение по годам, резерв и порядок согласования изменений?"},
    {"id": "risks", "topic": "Риски", "question": "Назовите три главных риска проекта и ранние признаки их наступления."},
]


def init_copilot_state(state: Any) -> None:
    defaults = {
        "copilot_messages": [],
        "copilot_facts": {},
        "copilot_wishes": [],
        "copilot_actions": [],
        "copilot_recommendations": [],
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


def next_guiding_question(state: Any, greenfield_project: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
    """Выбирает один следующий вопрос; не требует подключения к модели."""
    facts = state.copilot_facts
    profile = greenfield_project or {}

    # Специальные вопросы по подземному проекту.
    if profile.get("mine_method") == "подземный" and "method" in facts:
        special = [
            {"id": "ventilation", "topic": "Подземные работы", "question": "Как обеспечивается проветривание: ГВУ, схема выработок, этап ввода и исходные данные для расчета вентиляции?"},
            {"id": "dewatering", "topic": "Подземные работы", "question": "Как предусмотрены шахтный водоотлив, отстойник/очистка и отведение воды?"},
            {"id": "explosives", "topic": "Подземные работы", "question": "Как организуется снабжение ВМ: подрядчик, площадка перегрузки или склад; что входит в границы проекта?"},
        ]
        for item in special:
            if item["id"] not in facts:
                return item

    for item in QUESTION_BANK:
        if item["id"] not in facts:
            return item
    return None


def project_memory(state: Any) -> str:
    fact_lines = []
    for key, item in state.copilot_facts.items():
        fact_lines.append("- {0}: {1} ({2}; {3})".format(
            key, item.get("value", ""), item.get("source", ""), item.get("confidence", "")
        ))
    wish_lines = ["- " + text for text in state.copilot_wishes[-10:]]
    return (
        "ПОДТВЕРЖДЕННЫЕ И СОБРАННЫЕ ФАКТЫ:\n" + ("\n".join(fact_lines) or "—") +
        "\n\nПОЖЕЛАНИЯ РУКОВОДИТЕЛЯ ПРОЕКТА:\n" + ("\n".join(wish_lines) or "—")
    )


def fallback_reply(state: Any, user_text: str, greenfield_project: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Работает при отсутствии API-ключа или llm_assistant.py."""
    lower = user_text.lower()
    recommendations = []
    if any(word in lower for word in ["срок", "дедлайн", "задерж", "опоздан"]):
        recommendations.append("Зафиксируйте контрольную дату и назначьте владельцев критических ИРД.")
    if any(word in lower for word in ["подзем", "шахт", "рудник"]):
        recommendations.append("Проверьте вентиляцию, водоотлив, ВМ, ОПО и готовность инфраструктуры до начала проходки.")
    if any(word in lower for word in ["тз", "задани"]):
        recommendations.append("До выпуска ТЗ подтвердите предмет, границы этапа, ИРД, специальные разделы и маршрут экспертиз.")

    question = next_guiding_question(state, greenfield_project)
    answer = "Запрос зафиксирован. "
    if recommendations:
        answer += " ".join(recommendations)
    else:
        answer += "Чтобы корректно построить дорожную карту, нужно уточнить один критичный параметр."

    return {
        "answer": answer,
        "question": question["question"] if question else "Какой документ или управленческое решение подготовить следующим шагом?",
        "facts": [],
        "actions": [],
        "recommendations": recommendations,
    }


SYSTEM_PROMPT = """Ты — AI Project Copilot для greenfield-проектов добычи полезных ископаемых.
Помогаешь РП формировать дорожную карту, ТЗ, реестр ИРД, риски, график и бюджет.

Строгие правила:
- Не выдумывай номера лицензий, нормы, даты, статусы экспертиз и проектные решения.
- Разделяй подтвержденные факты, сведения пользователя и предположения.
- Для экспертиз и разрешений пиши: «проверить применимость профильным экспертом».
- Давай краткий вывод, до трех действий и ровно один следующий вопрос.
- Верни ТОЛЬКО валидный JSON следующей структуры:
{
  "answer":"краткий вывод",
  "question":"один следующий вопрос",
  "facts":[{"key":"краткий_ключ","value":"значение","source":"сообщил пользователь или документ; требует подтверждения"}],
  "actions":[{"title":"действие","owner":"роль","due_hint":"срок или условие","priority":"high"}],
  "recommendations":["рекомендация"]
}
"""


def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except ValueError:
                return None
    return None


def ai_reply(
    api_key: str,
    model_name: str,
    user_text: str,
    state: Any,
    search_results: List[Tuple],
    greenfield_project: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not (LLM_AVAILABLE and api_key and model_name in FREE_MODELS):
        return fallback_reply(state, user_text, greenfield_project)

    try:
        evidence = build_context(search_results) if search_results else "Релевантные фрагменты в загруженных документах не найдены."
        deterministic_question = next_guiding_question(state, greenfield_project)
        prompt = "{system}\n\n{memory}\n\nПРОФИЛЬ ПРОЕКТА:\n{profile}\n\nДОКУМЕНТЫ:\n{evidence}\n\n" \
                 "РЕКОМЕНДУЕМЫЙ СЛЕДУЮЩИЙ ВОПРОС:\n{question}\n\nСООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:\n{user}".format(
                    system=SYSTEM_PROMPT,
                    memory=project_memory(state),
                    profile=json.dumps(greenfield_project or {}, ensure_ascii=False, default=str),
                    evidence=evidence[:12000],
                    question=deterministic_question["question"] if deterministic_question else "Уточните требуемый результат.",
                    user=user_text,
                 )
        raw = ask_llm(api_key, prompt, "", FREE_MODELS[model_name])
        result = parse_json_response(raw)
        if result:
            return result
        return {
            "answer": str(raw),
            "question": deterministic_question["question"] if deterministic_question else "Что подготовить следующим шагом?",
            "facts": [], "actions": [], "recommendations": [],
        }
    except Exception as exc:
        result = fallback_reply(state, user_text, greenfield_project)
        result["answer"] = "ИИ временно недоступен: {0}. ".format(exc) + result["answer"]
        return result


def apply_ai_result(state: Any, result: Dict[str, Any]) -> None:
    for fact in result.get("facts", []):
        if not isinstance(fact, dict):
            continue
        key = str(fact.get("key", "")).strip()
        value = str(fact.get("value", "")).strip()
        if key and value:
            state.copilot_facts[key] = {
                "value": value,
                "source": fact.get("source", "AI-извлечение"),
                "confidence": "Требует подтверждения",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
    actions = result.get("actions", [])
    if isinstance(actions, list):
        state.copilot_actions.extend([item for item in actions if isinstance(item, dict)])
    recommendations = result.get("recommendations", [])
    if isinstance(recommendations, list):
        state.copilot_recommendations.extend([str(item) for item in recommendations])


def render_ai_copilot(
    state: Any,
    docs: List[Dict[str, Any]],
    search_fn: Any,
    greenfield_project: Optional[Dict[str, Any]] = None,
) -> None:
    init_copilot_state(state)

    st.header("🤖 AI Project Copilot")
    st.caption("Диалог по документам, дорожной карте, ТЗ и рискам. Рекомендации требуют проверки профильным специалистом перед утверждением.")

    with st.expander("Пожелания руководителя проекта", expanded=False):
        wish = st.text_area(
            "Что важно учесть в проекте?",
            placeholder="Например: ввод первой очереди — не позднее IV квартала 2028; инфраструктуру вести отдельными титулами; бюджет показывать в тыс. руб.",
            key="copilot_wish_input",
        )
        if st.button("Сохранить пожелание", key="save_copilot_wish") and wish.strip():
            state.copilot_wishes.append(wish.strip())
            st.success("Пожелание сохранено в памяти проекта.")

    api_key = ""
    model_name = ""
    with st.expander("⚙️ Настройки ИИ", expanded=False):
        if LLM_AVAILABLE and FREE_MODELS:
            api_key = st.text_input("API-ключ OpenRouter", value=state.get("api_key", ""), type="password", key="copilot_api_key")
            model_name = st.selectbox("Модель", list(FREE_MODELS.keys()), key="copilot_model")
        else:
            st.info("LLM-модуль или API-ключ не подключены. Работает режим проектной памяти и наводящих вопросов.")

    dialog_tab, facts_tab, actions_tab = st.tabs(["💬 Диалог", "🧠 Факты проекта", "✅ Действия"])

    with dialog_tab:
        for message in state.copilot_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if not state.copilot_messages:
            first_question = next_guiding_question(state, greenfield_project)
            if first_question:
                with st.chat_message("assistant"):
                    st.markdown("Начнем с критичного для управляемого запуска проекта.")
                    st.markdown("**{0}**".format(first_question["question"]))

        user_text = st.chat_input("Напишите ответ, пожелание или задачу: «сформируй ТЗ на ПД вскрытия»")
        if user_text:
            state.copilot_messages.append({"role": "user", "content": user_text})
            results = search_fn(user_text) if docs else []
            with st.spinner("AI Project Copilot анализирует документы и контекст..."):
                result = ai_reply(api_key, model_name, user_text, state, results, greenfield_project)
            apply_ai_result(state, result)
            content = result.get("answer", "")
            if result.get("question"):
                content += "\n\n**Следующий вопрос:** " + result["question"]
            state.copilot_messages.append({"role": "assistant", "content": content})
            st.rerun()

    with facts_tab:
        st.subheader("Факты и подтверждение")
        if not state.copilot_facts:
            st.info("Нет сохраненных фактов. Ответьте на вопрос в чате или загрузите документы.")
        for key, item in list(state.copilot_facts.items()):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown("**{0}:** {1}".format(key, item.get("value", "")))
                st.caption("{0} · {1}".format(item.get("confidence", ""), item.get("source", "")))
            with col2:
                if item.get("confidence") != "Подтверждено":
                    if st.button("Подтвердить", key="confirm_fact_" + key):
                        item["confidence"] = "Подтверждено"
                        item["source"] = "Подтверждено пользователем"
                        st.rerun()

    with actions_tab:
        st.subheader("Действия и рекомендации")
        if not state.copilot_actions:
            st.info("После первого диалога здесь появятся предложенные действия.")
        for action in state.copilot_actions[-20:]:
            priority = action.get("priority", "medium")
            icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(priority, "🔵")
            st.markdown("{0} **{1}** · {2}".format(icon, action.get("title", "Действие"), action.get("owner", "владелец не назначен")))
            if action.get("due_hint"):
                st.caption("Срок / условие: " + action["due_hint"])
        if state.copilot_recommendations:
            st.markdown("**Рекомендации**")
            for recommendation in list(dict.fromkeys(state.copilot_recommendations[-20:])):
                st.markdown("- " + recommendation)
```

```python
# app.py — импорт и вызов
# Замените старый импорт на этот:
from ai_project_copilot import render_ai_copilot

# В ветке меню:
elif menu.startswith("🤖"):
    render_ai_copilot(
        state=S,
        docs=S.docs,
        search_fn=search_knowledge,
        greenfield_project=S.get("gf_project", {}),
    )
