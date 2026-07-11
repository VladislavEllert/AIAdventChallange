# RAG Evaluation — Day 28

Model: `ollama/qwen3:4b` | Index: fixed | threshold=0.5 | threshold_answer=0.55 | top_k=5 | query_rewrite=ON

---

## Q1: Какова политика GitLab в отношении оплачиваемого отпуска? Сколько дней получают сотрудники?

**Expected:** Гибкая политика PTO (~25 рабочих дней); фиксированного числа нет; сотрудников поощряют брать отпуск

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.643

**Sources in answer:** ✅

### Without RAG
GitLab предоставляет сотрудникам **20 оплачиваемых дня отпуска в год**. Эта политика указана в их официальной документации, включая разделы по работе и жизни (Work-Life policy). Отпускные дни учитываются как часть стандартного рабочего времени и не зависят от региона, так как компания использует глобальную модель управления. Дополнительно GitLab предоставляет специальные дни отпуска для родителей и других обстоятельств, но основной оплачиваемый отпуск составляет 20 дней в год.

### With RAG
К сожалению, в предоставленных контекстах GitLab Handbook нет информации о политиках в отношении оплачиваемого отпуска и количестве дней, которые получают сотрудники. Все разделы, которые были показаны (коммуникация, безопасность, ценности, люди/группа), фокусируются на общих принципах работы, ценностях компании и рекомендациях по коммуникации, но не содержат данных о правовых или кадровых политиках включая отпуск.

**Sources:**  
- https://handbook.gitlab.com/handbook/communication/ (Context [1] and [4])  
- https://handbook.gitlab.com/handbook/security/ (Context [2])  
- https://handbook.gitlab.com/handbook/values/ (Context [3])  
- https://handbook.gitlab.com/handbook/people-group/ (Context [5])  

*Краткий анализ: В предоставленных источниках отсутствует специфическая информация о политике оплачиваемого отпуска и количестве дней. Для получения точной информации необходимо обратиться к другим разделам GitLab Handbook, например, к разделу "People and Work" или "Compensation and Benefits" в документации.*

---

## Q2: Какой срок установлен для ответа ревьюера на запрос code review в GitLab? Что он обязан сделать, если не успевает?

**Expected:** Не более 36 часов; уведомить автора и помочь найти другого ревьюера

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.655

**Sources in answer:** ✅

### Without RAG
В GitLab по умолчанию не установлен срок ответа ревьюера на запрос code review. Если администратор проекта настроил лимит времени (например, 24 часа), то ревьюер обязан отвечать в указанный срок. В случае отсутствия ответа GitLab автоматически отправляет уведомление о задержке, но ревьюер не обязан принимать дополнительные действия — система сама оформляет ревью как "overdue".

### With RAG
В GitLab срок ответа ревьюера на запрос code review определяется SLO (Service Level Objectives) для ответа. Согласно документации, если ревьюер не успевает ответить в течение установленного SLO, он обязан:  
1. Уведомить автора merge request в комментариях **не позднее 36 часов** после первого получения запроса на ревью;  
2. Помочь найти другого ревьюера или поддержки, чтобы автор мог продолжить работу;  
3. Удалить себя из списка ревьюеров.  

Это регламентировано в разделе "Review-response SLO" Code Review Guidelines.  

Sources:  
- [1] https://handbook.gitlab.com/handbook/engineering/workflow/code-review/ (описание обязательности кодовых обзоров и SLO по времени ответа)  
- [2] https://handbook.gitlab.com/handbook/engineering/workflow/code-review/ (удаление ревьюера и действия в случае задержки)  
Quote: *"a merge request in the `Review-response` SLO time frame, let the author know as soon as possible in the comments (no later than 36 hours after first receiving the review request) and try to help them find another reviewer or maintainer who is able to, so that they can be unblocked and get on with their work quickly. Remove yourself as a reviewer."*

---

## Q3: Как GitLab обращается с отпуском по уходу за ребёнком?

**Expected:** 16 недель оплачиваемого отпуска для любого сотрудника вне зависимости от пола; подробности в leave-types

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.653

**Sources in answer:** ✅

### Without RAG
GitLab как компания предоставляет сотрудникам отпуск по уходу за ребёнком в соответствии с местными законодательством и внутренней политикой компании. Обычно такие отпуска включают определённое количество дней (например, 2–4 недели), но точные условия зависят от страны и региона деятельности компании. Для получения подробной информации рекомендуется проверить официальную политику HR GitLab на их сайте.

### With RAG
Я не могу ответить на этот вопрос, так как предоставленный контекст не содержит информации о политике отпусков по уходу за ребенком в GitLab. None of the handbook excerpts (Communication, Security, Values, People Group) discuss parental leave policies or childcare leave arrangements.

**Sources:**  
https://handbook.gitlab.com/handbook/communication/  
https://handbook.gitlab.com/handbook/security/  
https://handbook.gitlab.com/handbook/communication/  
https://handbook.gitlab.com/handbook/values/  
https://handbook.gitlab.com/handbook/people-group/

---

## Q4: Что значит «power harassment» по определению в политике GitLab?

**Expected:** Использование должностных полномочий для причинения психического стресса, физической боли или ухудшения рабочей обстановки

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.721

**Sources in answer:** ✅

### Without RAG
В политике GitLab термин «power harassment» определяется как **систематическое использование власти или позиции ответственности для психологического давления, манипуляции или негативного воздействия на сотрудника или группу людей**, что создает ущерб для их психического здоровья, карьерного роста или благополучия. Это включает в себя угрозы, подавление, злоупотребление авторитетом и другие действия, направленные на нарушение этических норм и безопасной рабочей среды. Такое определение соответствует принципам GitLab, которые акцентируют внимание на инклюзивности, уважении к сотрудникам и предотвращении агрессивного поведения в высокоприоритетных структурах.

### With RAG
По определению в политике GitLab (в разделе для GitLab GK в Японии), «power harassment» (POWER HARASSMENT) — это любые действия лица, использующего свою власть в рабочей среде (например, должность или человеческие отношения с коллегой), за пределами допустимого круга профессионального поведения, которые вызывают у коллеги психологическое беспокойство, физическую боль или деградацию рабочей среды.

Sources:  
- https://handbook.gitlab.com/handbook/people-group/anti-harassment/  
С краткой цитатой: "Power harassment" is defined as any act by a person using his/her authority in the workplace, such as job position or human relationship with a team member, beyond the appropriate scope of business conduct, which causes such team member mental distress or physical pain or degradation of the working environment.

---

## Q5: Через какую систему подаётся заявка на декретный отпуск в GitLab для сотрудников в США? Сколько времени занимает обработка?

**Expected:** Tilt (через Okta); уведомление Absence Management Team через HelpLab-тикет

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.619

**Sources in answer:** ✅

### Without RAG
Сотрудники в США GitLab подают заявку на декретный отпуск через внутреннюю систему управления отпуском компании (например, HR-портал или специализированный интерфейс). Обработка заявки обычно занимает до 5 рабочих дней, однако точное время может варьироваться в зависимости от внутренних процессов компании.

### With RAG
Соблюдение условий задачи: ответ основывается только на предоставленных контекстах. В предоставленных эзекциях (1-5) отсутствует информация о системе подачи заявок на декретный отпуск в GitLab для сотрудников в США и времени обработки. Детали по отпускам, включая декретные, не упомянуты в разделах безопасности, коммуникации, ценностях или People Group.

Sources:
- https://handbook.gitlab.com/handbook/security/
- https://handbook.gitlab.com/handbook/communication/
- https://handbook.gitlab.com/handbook/values/
- https://handbook.gitlab.com/handbook/people-group/

Short quote: "Welcome to the People Group handbook! You should be able to find answers to most of your questions here." (Source [5])

---

## Q6: Как в GitLab проводят анализ причин инцидента после сбоя?

**Expected:** Прозрачный процесс; любой сотрудник может провести RCA; фокус на «что пошло хорошо, что нет»

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.641

**Sources in answer:** ✅

### Without RAG
В GitLab анализ причин инцидента после сбоя проводится следующим образом:

1. **Создание инцидента через GitLab Incidents** (начиная с версии 14.0):  
   Используются встроенные инструменты для создания и отслеживания инцидентов, включая сбор данных о сбое, логи и метрики.

2. **Сбор данных**:  
   - Анализ логов CI/CD pipelines (через GitLab Runs).  
   - Интеграция с мониторингом (например, через GitLab Monitor, Prometheus или Grafana).  
   - Логи систем и сервисов (через инструменты вроде ELK).

3. **Анализ корневой причины (RCA)**:  
   Применяются методы вроде 5 Whys или Fishbone diagram для определения истинной причины сбоя, например, ошибки в коде, недостаточная проверка в pipeline или проблемы с зависимостями.

4. **Генерация рекомендаций и исправление**:  
   На основе анализа создаются меры по предотвращению повторения сбоев (например, обновление CI/CD-процедур или добавление тестов).

Дополнительно: Если сбой произошёл в CI/CD pipeline, GitLab автоматически предоставляет детали ошибки, логи шагов и информацию о том, где именно произошёл сбой, что упрощает диагностику.

Этот процесс интегрируется в общую систему управления инцидентами GitLab, позволяя быстро реагировать на сбои и улучшать процессы.

### With RAG
На основе предоставленного контекста не могу определить, как в GitLab проводят анализ причин инцидента после сбоя. В доступных экземплярах GitLab Handbook (Communication, Security, Values) отсутствует информация о процессах анализа инцидентов, пост-инцидентном расследовании или аналогичных операциях. Контекст содержит рекомендации по коммуникации, принципам безопасности и ценностям компании, но не описывает инцидентную отчётность или методы анализа сбоев.

Sources:  
- https://handbook.gitlab.com/handbook/communication/  
- https://handbook.gitlab.com/handbook/security/  
- https://handbook.gitlab.com/handbook/values/

---

## Q7: Сколько собак можно иметь сотруднику GitLab?

**Expected:** Не по теме — в Handbook нет лимита на собак; embedding может ложно зацепиться за 'supportive environment' формулировки

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.663

**Sources in answer:** ✅

### Without RAG
0

### With RAG
The provided context from GitLab's Handbook does not contain any information about how many dogs an employee can own. The handbook excerpts cover topics like communication standards, security practices, core values, and project naming conventions, but there are no references to dog ownership policies or related guidelines.

**Sources:**  
- [GitLab Communication Handbook](https://handbook.gitlab.com/handbook/communication/)  
- [GitLab Security Handbook](https://handbook.gitlab.com/handbook/security/)  
- [GitLab Values Handbook](https://handbook.gitlab.com/handbook/values/)  
- A short quote from the context: *"Avoid using Git in the naming of internal and external company related programs (BagGit, GitFit, Gitty, GitIt, etc.)."* (Source [5])

*No information about dog ownership policies is present in the provided handbook excerpts.*

---

## Q8: Какая порода кошки лучше всего подходит для офиса GitLab?

**Expected:** Не по теме — в Handbook нет ничего про кошек/офисных животных; HR-лексика может дать обманчиво высокий score

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.639

**Sources in answer:** ✅

### Without RAG
The "best" cat breed for a GitLab office doesn't exist — but the Unix `cat` command (which displays file contents) is the perfect solution! 😄

### With RAG
Контекст, предоставленный в задании, не содержит информации о породах кошек и их использовании в офисе GitLab. Все доступные разделы GitLab Handbook (коммуникация, безопасность, ценности) фокусируются на рабочих процессах, принципах безопасности и ценностях компании, но не упоминают животных или рекомендации по породам кошек для офиса.

**Sources:**  
- [1] https://handbook.gitlab.com/handbook/communication/ (разделы про коммуникацию)  
- [2] https://handbook.gitlab.com/handbook/security/ (разделы про безопасность)  
- [3] https://handbook.gitlab.com/handbook/values/ (разделы про ценности)  
- [4] https://handbook.gitlab.com/handbook/communication/ (предупреждения по названиям проектов)  
- [5] https://handbook.gitlab.com/handbook/communication/ (правила электронной почты и экспорта в Slack)  

Краткая цитата из контекста: *"Avoid using Git in Project Names Avoid using *Git* in the naming of internal and external company related programs..."* — но эта информация не относится к вопросу о кошках.

---

## Q9: Как лучше жарить картошку с луком?

**Expected:** Полностью не по теме, никакой связи с GitLab Handbook — ожидается низкий similarity score

**RAG stats:** raw=20 → kept=0 → final=0 | best_score=0.438

**Sources in answer:** ❌

### Without RAG
Чтобы лучше жарить картошку с луком, сделайте следующее:

1. **Нарезьте ингредиенты**:  
   — Лук мелко нарезайте кубиками (1–2 см).  
   — Картошку очистите и нарежьте кубиками одинакового размера (1–1,5 см).

2. **Жарка**:  
   — В сковороде нагревайте растительное масло (1–2 ст. ложки).  
   — Сначала обжарите лук на среднем огне 2–3 минуты до прозрачности.  
   — Добавьте картошку, перемешайте и жарьте ещё 5–7 минут на среднем огне, пока картошка не станет золотистой и не слегка поджарится.

3. **Добавьте соль**:  
   — После жарки добавьте соль по вкусу и перемешайте.

**Важно**:  
— Не перегревайте, чтобы картошка не осталась сухой.  
— Если картошка жарится слишком быстро, уменьшите огонь или налейте немного воды (опционально).  
— Для лучшего вкуса можно добавить мятный сок или чеснок перед жаркой.

Подавайте сразу после жарки — картошка будет нежной и сочной! 😊

### With RAG
К сожалению, в предоставленном контексте нет информации о том, как лучше жарить картошку с луком. GitLab Handbook не содержит кулинарные рецепты, поэтому для данного вопроса требуется обратиться к кулинарным ресурсам, а не к GitLab.

Sources:  
- URL: Not applicable  
- Quote: "Context: (no relevant context found)"

---

## Q10: Есть ли у GitLab дресс-код для видеозвонков?

**Expected:** Не по теме — в Handbook нет дресс-кода; пограничный случай, звучит как правдоподобный HR-вопрос

**RAG stats:** raw=20 → kept=20 → final=5 | best_score=0.607

**Sources in answer:** ✅

### Without RAG
Нет, у GitLab нет дресс-кода для видеозвонков. GitLab — это инструмент для управления проектами и разработки, а видеозвонки не являются его функционалом. Такой термин как "дресс-код" в контексте видеозвонков здесь не применим, так как GitLab не предоставляет встроенные возможности для проведения видеозвонков. Если вы имеете в виду рекомендации по использованию видеозвонков в процессах GitLab (например, через интеграцию с сервисами вроде Zoom), это не связано с официальным дресс-кодом.

### With RAG
Я не знаю. В предоставленных источниках GitLab Handbook отсутствует информация о дресс-коде для видеозвонков.

Sources:
- https://handbook.gitlab.com/handbook/communication/ | "GitLab is an internationally diverse company. US-based team members should not refer to team members outside the US as 'international'."

---

## Don't-Know Gate Test

**Question:** What is the current weather in Moscow today?

**Best score:** 0.472 (threshold_answer=0.55)

**Triggered:** ✅ YES — model says "I don't know"

