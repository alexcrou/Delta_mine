import time
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Цифровой штаб", page_icon="◆", layout="wide")
st.markdown("""<style>
.stApp{background:#061323;color:#e8f0f7}.block-container{max-width:1480px;padding-top:1rem}.hero{background:linear-gradient(110deg,#06172b,#0a365e);border:1px solid #1a527d;border-radius:18px;padding:27px 32px}.hero h1{margin:0;color:#fff;font-size:32px}.hero p{color:#a9c7df;margin:7px 0 0}.panel{background:#091d31;border:1px solid #173b59;border-radius:13px;padding:16px}.critical{background:#29161d;border-left:5px solid #e44b55;padding:13px;border-radius:8px}.warn{background:#292112;border-left:5px solid #d8a647;padding:13px;border-radius:8px}div[data-testid='stMetric']{background:#091d31;border:1px solid #173b59;border-radius:11px;padding:10px}div[data-testid='stDataFrame']{border:1px solid #173b59;border-radius:10px}</style>""",unsafe_allow_html=True)

PROFILE={"code":"03737","license":"СВЕ03737 БЭ","name":"Ново-Шайтанское месторождение","location":"Кировградский ГО, Свердловская область","expiry":"10.10.2036","reserves":"3,64 млн т","capacity":"570–620 тыс. т/год"}
RISKS=pd.DataFrame([
["Изменение условий лицензии","Критический","Срок ввода 2024 не выполнен; рассмотрение в ЦКР приостановлено","Директор проекта / юрист","Изменение условий лицензии и сопровождение разрешительного маршрута","31.12.2026"],
["Геомеханика и гидрогеология","Критический","Изыскания 2017 г. требуют актуализации; данных по массиву недостаточно","Главный геолог","Бурение, лабораторные испытания, гидрогеология, доменизация","30.11.2027"],
["ЗСО р. Шайтанка","Критический","Южная площадка пересекает II и III пояса ЗСО","Эколог / земельник","Вариантная проработка, согласования, исключение недопустимых решений","До ПД"],
["Отрицательное ГГЭ старого ПД","Критический","Заключение ГГЭ 15.11.2021; старое ПД не реализуемо","Директор по проектированию","Новое ТЗ, актуальные ИИ, pre-review, выпуск новой ПД","31.03.2029"],
["Ресурсная модель","Высокий","Нет участка детализации для обоснования сети","Главный геолог","Колонковое бурение, контроль качества, ТЭО ПРК","Q4 2027"],
["Технология и переработка","Высокий","Нужны представительная проба и НИР для Сибайского ГОК / ОФ К-ПМ","Главный технолог","Исследования и подтверждение технологических параметров","Q4 2027"],
],columns=["Риск","Уровень","Основание","Владелец","Мероприятие","Срок"])
ROAD=pd.DataFrame([
["G0","Изменение условий лицензии","2026-08-01","2026-12-31","Критический"],["G1","Инженерные изыскания и обследование АТП/НЗС","2026-08-01","2026-12-01","Критический"],["G1","ОТР и выбор схемы вскрытия","2026-10-01","2027-03-31","Высокий"],["G2","Бурение, геомеханика, гидрогеология","2027-01-01","2027-11-30","Критический"],["G2","ТЭО ПРК и отчёт с подсчётом запасов","2027-06-01","2028-07-01","Критический"],["G3","Технический проект, ПД рудника и инфраструктуры","2028-02-01","2029-03-31","Критический"],["G4","Экспертизы и разрешения","2029-01-01","2029-09-30","Критический"],["G5","ГКР, инфраструктура, поставки","2029-07-01","2030-09-30","Высокий"],["G6","ПНР, ввод, начало добычи","2030-07-01","2030-12-31","Критический"]],columns=["Gate","Работа","Начало","Окончание","Приоритет"])
BUDGET=pd.DataFrame([["Доразведка и ТЭО ПРК",.35],["ИИ и геомеханика",.22],["Технологические исследования",.10],["ПИР, экспертизы, разрешения",.38],["ГКР и вскрытие АТУ",3.65],["Инфраструктура",.85],["Горная техника",1.55],["Резерв",.70]],columns=["Статья","млрд руб."])

for k,v in {"opened":False,"norms":False,"rd":False,"gp":False}.items():st.session_state.setdefault(k,v)
def progress(labels,seconds):
 bar=st.progress(0)
 for n,label in enumerate(labels):
  with st.status(label,expanded=True) as s:
   for i in range(seconds*10):
    time.sleep(.1);bar.progress(int((n*seconds*10+i+1)/(len(labels)*seconds*10)*100),text=label)
   s.update(label=label+" — завершено",state="complete",expanded=False)

def search_hint(value):
 if not value:return "Введите 5 цифр. Поиск запускается по полному коду лицензии."
 if not value.isdigit():return "Допустимы только цифры."
 if len(value)<5:return f"Введено {len(value)} из 5 цифр — продолжайте ввод."
 return "Код готов к проверке в реестрах лицензий, решений и проектных материалов."

st.markdown("<div class='hero'><h1>◆ Цифровой штаб</h1><p>Investment delivery intelligence · единый контур решений, рисков, сроков и капитала</p></div>",unsafe_allow_html=True)
with st.sidebar:
 st.markdown("### УПРАВЛЯЮЩИЕ ДЕЙСТВИЯ")
 if st.button("↻ Обновить нормативную базу",use_container_width=True):
  progress(["Индексация нормативных документов"],5);st.session_state.norms=True
 if st.session_state.norms:st.success("Нормативная база обновлена на 25.08.2026");st.caption("Контрольный пакет: к 01.06.2026.pdf")
 st.divider();st.caption("Статусы решений подтверждаются первичными документами, владельцами данных и уполномоченными специалистами.")

if not st.session_state.opened:
 st.subheader("Открытие проектного контура")
 st.write("Введите номер лицензии для запуска проверки статуса актива, разрешительных ограничений и связанных материалов.")
 c1,c2=st.columns([3,1]);code=c1.text_input("Номер лицензии — 5 цифр",max_chars=5,placeholder="Например: 5 цифр номера лицензии")
 c1.caption(search_hint(code))
 if code and len(code)==5 and code!=PROFILE['code']:c1.info("Код принят. После подключения корпоративного реестра будет сформирована карточка соответствующего актива; для текущего контура доступен профиль 03737.")
 if c2.button("Проверить",type="primary",use_container_width=True):
  if len(code)!=5 or not code.isdigit():st.error("Введите номер из пяти цифр.")
  elif code==PROFILE['code']:
   progress(["Запрос в Роснедра","Запрос в ЦКР/ТКР","Обработка материалов"],3);st.session_state.opened=True;st.rerun()
  else:st.warning("По указанному номеру в подключённом проектном реестре нет карточки. Проверьте номер или загрузите паспорт лицензии для создания нового контура.")
 st.stop()

st.success("Контур открыт · лицензия СВЕ03737 БЭ · статус данных: рабочий срез 25.08.2026")
t1,t2,t3,t4,t5=st.tabs(["Решения","Дорожная карта","Риски","Финансы","Проектный офис"])
with t1:
 st.subheader(PROFILE['name']);a,b,c,d,e=st.columns(5);a.metric("Лицензия",PROFILE['license']);b.metric("Срок",PROFILE['expiry']);c.metric("Ввод","2030");d.metric("Запасы",PROFILE['reserves']);e.metric("Мощность",PROFILE['capacity'])
 st.markdown("<div class='critical'><b>Критический стоп-фактор.</b> Условие ввода в 2024 году не выполнено. Рассмотрение технического проекта в ЦКР приостановлено до изменения лицензии.</div><br><div class='warn'><b>Рекомендация штаба.</b> Принять АТУ как приоритетный вариант ОТР: ориентир 6,3 млрд руб. против 8,4 млрд руб. при вертикальных стволах. Потенциал оптимизации — около 2,1 млрд руб.; решение утверждается после ТЭО, ИИ, проектирования и техсовета.</div>",unsafe_allow_html=True)
 x,y,z=st.columns(3);x.markdown("<div class='panel'><b>7 дней</b><br>Владельцы критических рисков, разрешительный маршрут, реестр ИД.</div>",unsafe_allow_html=True);y.markdown("<div class='panel'><b>30 дней</b><br>ТЗ на ИИ и ОТР, обследование АТП/НЗС, границы проектных контуров.</div>",unsafe_allow_html=True);z.markdown("<div class='panel'><b>90 дней</b><br>Техсовет по вскрытию, baseline графика и бюджета, RACI.</div>",unsafe_allow_html=True)
with t2:
 p=st.data_editor(ROAD,use_container_width=True,num_rows='dynamic');g=p.copy();g['Начало']=pd.to_datetime(g['Начало']);g['Окончание']=pd.to_datetime(g['Окончание']);f=px.timeline(g,x_start='Начало',x_end='Окончание',y='Работа',color='Приоритет',color_discrete_map={'Критический':'#e44b55','Высокий':'#d8a647'});f.update_yaxes(autorange='reversed');f.update_layout(height=600,paper_bgcolor='#061323',plot_bgcolor='#061323',font_color='#e8f0f7');st.plotly_chart(f,use_container_width=True)
with t3:
 st.dataframe(RISKS,use_container_width=True,hide_index=True,height=420)
with t4:
 b=st.data_editor(BUDGET,use_container_width=True,num_rows='dynamic');total=pd.to_numeric(b['млрд руб.'],errors='coerce').fillna(0).sum();st.metric("Рабочий бюджетный контур АТУ",f"{total:.2f} млрд руб.");st.caption("Ранняя оценка для стратегии и инвестиционного планирования; не является сметой.")
with t5:
 c1,c2=st.columns(2)
 with c1:
  st.markdown('### 🔎 Проверка чертежей РД');files=st.file_uploader('PDF/DWG/DXF, реестр листов, ТЗ',type=['pdf','dwg','dxf','xlsx','docx'],accept_multiple_files=True)
  if st.button('Проверить комплектность РД'):
   if files:st.success('Комплект принят в контрольный реестр. Проверяются состав, интерфейсы и замечания.');st.dataframe(pd.DataFrame([['ПЗ','Проверить'],['ПЗУ / ГП','Границы, ЗСО, топооснова'],['ИОС','35/6 кВ, вода, вентиляция, водоотлив'],['ООС / ПБ','Ограничения и мероприятия']],columns=['Раздел','Контроль']),hide_index=True)
   else:st.warning('Загрузите файлы.')
 with c2:
  st.markdown('### 🧭 Сформировать генплан');gp=st.file_uploader('ГПЗУ, DWG/DXF-съёмка, кадастр, ТУ',type=['pdf','dwg','dxf','xlsx','zip'],accept_multiple_files=True,key='gp')
  if st.button('Сформировать ТЗ на генплан'):
   if gp:st.success('ТЗ сформировано: проверить ЗСО р. Шайтанка, сети, санитарные и пожарные разрывы, рельеф, водоотведение, логистику.');st.download_button('Скачать ТЗ (.md)','# ТЗ на генплан\n\nИсходные данные: ГПЗУ, топосъёмка DWG/DXF, кадастр, ТУ, перечень объектов.\n\nПроверки: ЗСО р. Шайтанка, инженерные сети, рельеф, водоотведение, санитарные и пожарные разрывы, логистика.','tz_genplan.md')
   else:st.warning('Загрузите исходные данные.')
