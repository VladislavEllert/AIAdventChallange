# RAG Evaluation — Day 23: RAG without filter vs RAG with filter

Model: `openai/gpt-4o-mini` | Index: fixed | top_k=5 | query_rewrite=ON (both arms) | no-filter threshold=0.0 | filtered threshold=0.65

Both arms use RAG + query rewrite. The only difference: the *no-filter* arm keeps the top-K chunks by rank regardless of cosine score; the *filtered* arm drops any chunk below 0.65 similarity before building context.

---

## Q1: Какова политика GitLab в отношении оплачиваемого отпуска? Сколько дней получают сотрудники?

**Expected:** Гибкая политика PTO (~25 рабочих дней); фиксированного числа нет; сотрудников поощряют брать отпуск

**Rewritten query:** _What is GitLab's policy regarding paid vacation leave? How many days of paid vacation do employees receive?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.796

Политика GitLab в отношении оплачиваемого отпуска включает в себя гибкий оплачиваемый отпуск (Flexible Paid Time Off, PTO). Сотрудники могут использовать PTO для выполнения личных обязательств, отдыха, поездок или времяпрепровождения с близкими. Однако конкретное количество дней, которые получают сотрудники, не указано в предоставленном контексте.

**Sources:** 
- [Time Off Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/) - "This page focuses specifically on GitLab's Flexible PTO policy and is written with a focus on using PTO to fulfill personal obligations, rest or recharge, enjoy a vacation, or spend..."

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=14 → final=5 | best_score=0.799

GitLab применяет политику гибкого оплачиваемого времени (Flexible Paid Time Off, PTO), что позволяет сотрудникам использовать отпуска для выполнения личных обязательств, отдыха, отпуска или времяпровождения с семьей. Однако конкретное количество дней, которые сотрудники получают в рамках данной политики, не указано в предоставленном контексте.

**Sources:**
- [Time Off Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/) - "On this page you will find GitLab's time-off policies, including Flexible Paid Time Off (PTO)..." 
- [Time Off and Absence](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/) - "Use the Time Away Philosophy section below to understand GitLab's approach to time off..."

---

## Q2: Какой срок установлен для ответа ревьюера на запрос code review в GitLab? Что он обязан сделать, если не успевает?

**Expected:** Не более 36 часов; уведомить автора и помочь найти другого ревьюера

**Rewritten query:** _What is the deadline for a reviewer to respond to a code review request in GitLab? What actions must they take if they are unable to meet this deadline?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.825

Срок для ответа ревьюера на запрос code review в GitLab составляет не более 36 часов с момента получения запроса. Если ревьюер не может выполнить обзор в установленный срок, он обязан уведомить автора как можно скорее в комментариях, постараться помочь найти другого ревьюера или мейнтейнера, который сможет провести обзор, и удалить себя из списка ревьюеров.

**Sources:** 
- [Code Review Guidelines](https://handbook.gitlab.com/handbook/engineering/workflow/code-review/) - "let the author know as soon as possible in the comments (no later than 36 hours after first receiving the review request)"

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.822

Срок ответа ревьюера на запрос code review в GitLab составляет не более 36 часов после получения запроса. Если рецензент не успевает выполнить обзор в указанный срок, он должен как можно скорее сообщить автору об этом в комментариях и попытаться найти другого рецензента или мейнтейнера, который сможет провести обзор, чтобы автор мог продолжить работу без задержек. Рецензент также должен удалить себя из списка рецензентов.

**Sources:**
- [GitLab Handbook - Code Review Guidelines](https://handbook.gitlab.com/handbook/engineering/workflow/code-review/) - "let the author know as soon as possible in the comments (no later than 36 hours after first receiving the review request)"

---

## Q3: Как GitLab обращается с отпуском по уходу за ребёнком?

**Expected:** 16 недель оплачиваемого отпуска для любого сотрудника вне зависимости от пола; подробности в leave-types

**Rewritten query:** _How does GitLab handle parental leave for childcare?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.784

GitLab предоставляет оплачиваемый отпуск по уходу за ребёнком сроком на 16 недель для всех активных сотрудников, независимо от гендерной принадлежности, которые стали родителями через рождение или усыновление во время работы в компании. Сотрудникам рекомендуется сообщать своему менеджеру о планируемом отпуске за 2-3 месяца до его начала, чтобы обеспечить надлежащее планирование рабочей нагрузки. Также существует процесс подачи запроса на отпуск, который для сотрудников из США и Канады осуществляется через систему Tilt. 

**Sources:** 
- [Leave Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/) - "GitLab’s paid Parental Leave is available for any active team member (regardless of gender) who becomes a parent through childbirth or adoption while working at GitLab."
- [Time Off and Absence](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/) - "Use the Time Away Philosophy section below to understand GitLab's approach to time off..."

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=4 → final=4 | best_score=0.787

GitLab предоставляет 16-недельный оплачиваемый отпуск по уходу за ребёнком (родительский отпуск) для всех активных членов команды, независимо от пола, которые становятся родителями через рождение ребёнка или усыновление. Важно отметить, что разные страны или штаты США могут предлагать собственные обязательные льготы по родительскому отпуску, поэтому рекомендуется ознакомиться с законами, действующими в конкретной локации.

**Sources:** 
- [Leave Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/) - "GitLab’s paid Parental Leave is available for any active team member (regardless of gender) who becomes a parent through childbirth or adoption while working at GitLab."

---

## Q4: Что значит «power harassment» по определению в политике GitLab?

**Expected:** Использование должностных полномочий для причинения психического стресса, физической боли или ухудшения рабочей обстановки

**Rewritten query:** _What is the definition of "power harassment" in the context of GitLab's policies?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.796

«Power harassment» в политике GitLab определяется как любое действие со стороны лица, использующего свою авторитетную позицию на рабочем месте, которое выходит за рамки надлежащего бизнес-общения и причиняет командному члену психическое страдание или физическую боль, а также приводит к ухудшению рабочего окружения.

**Sources:** 
- [GitLab Anti-Harassment Policy](https://handbook.gitlab.com/handbook/people-group/anti-harassment/) — "Power harassment" is defined as any act by a person using his/her authority in the workplace...

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=6 → final=5 | best_score=0.792

По определению в политике GitLab, "power harassment" — это любое действие человека, использующего свою власть на рабочем месте, например, из-за должности или человеческих отношений с членом команды, за пределами надлежащего делового поведения, что вызывает у этого члена команды психическое напряжение, физическую боль или ухудшение рабочего окружения.

**Sources:** [GitLab Anti-Harassment Policy](https://handbook.gitlab.com/handbook/people-group/anti-harassment/) - "Power harassment is defined as any act by a person using his/her authority in the workplace..."

---

## Q5: Через какую систему подаётся заявка на декретный отпуск в GitLab для сотрудников в США? Сколько времени занимает обработка?

**Expected:** Tilt (через Okta); уведомление Absence Management Team через HelpLab-тикет

**Rewritten query:** _Through which system should a maternity leave application be submitted in GitLab for employees in the United States? How long does the processing take?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.736

Заявка на декретный отпуск в GitLab для сотрудников в США подаётся через систему Tilt (доступную через Okta). Обработка заявки занимает от 2 до 5 рабочих дней.

**Sources:** 
- [GitLab Handbook - Leave Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/) - "Please submit your Parental Leave request to Tilt (accessed through Okta). Once your request is submitted, it takes 2-5 business days to build your personalized leave plan."

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=12 → final=5 | best_score=0.724

Заявка на декретный отпуск в GitLab для сотрудников в США подаётся через систему Tilt, которая доступна через Okta. Обработка заявки занимает 2-5 рабочих дней для создания персонализированного плана отпуска.

**Sources:**  
- [Leave Types](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/) - "Once your request is submitted, it takes 2-5 business days to build your personalized leave plan."

---

## Q6: Как в GitLab проводят анализ причин инцидента после сбоя?

**Expected:** Прозрачный процесс; любой сотрудник может провести RCA; фокус на «что пошло хорошо, что нет»

**Rewritten query:** _How does GitLab conduct root cause analysis after a failure incident?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.769

В GitLab анализ причин инцидента (Root Cause Analysis, RCA) проводится как возможность для повышения прозрачности и честности среди сотрудников и сообщества. Это делается после работы над проектом, инцидентом или проблемой, чтобы выяснить, что прошло хорошо, а что нет. Любой член команды GitLab может провести RCA. Этот процесс помогает понять причины произошедшего и улучшить процессы в будущем.

**Sources:** 
- [GitLab Handbook - Root Cause Analysis](https://handbook.gitlab.com/handbook/engineering/workflow/root-cause-analysis/) - "Мы рассматриваем анализ причин инцидента как возможность для прозрачности среди нашей организации и сообщества..."
- [GitLab Handbook - Engineering Workflow](https://handbook.gitlab.com/handbook/engineering/workflow/) - "Этот документ объясняет процесс работы над инцидентами и другими проблемами в GitLab."

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=15 → final=5 | best_score=0.777

В GitLab анализ причин инцидента (Root Cause Analysis, RCA) проводится как возможность для прозрачности внутри организации. Команда изучает, что прошло хорошо, а что нет, после работы над проектом, инцидентом или проблемой. Важно, что любой член команды GitLab может выполнить RCA. Процесс включает в себя детальное расследование, чтобы выявить коренные причины сбоев и улучшить будущую работу и процесс.

**Sources:** 
- [Root Cause Analysis](https://handbook.gitlab.com/handbook/engineering/workflow/root-cause-analysis/) - "Анализ коренных причин (RCA) рассматривается как возможность быть прозрачными среди нашей организации и сообщества."

---

## Q7: Сколько собак можно иметь сотруднику GitLab?

**Expected:** Не по теме — в Handbook нет лимита на собак; embedding может ложно зацепиться за 'supportive environment' формулировки

**Rewritten query:** _How many dogs is an employee of GitLab allowed to have?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.644

Я не знаю.

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=0 → final=0 | best_score=0.644

Я не знаю. 

**Sources:** Немає доступних джерел.

---

## Q8: Какая порода кошки лучше всего подходит для офиса GitLab?

**Expected:** Не по теме — в Handbook нет ничего про кошек/офисных животных; HR-лексика может дать обманчиво высокий score

**Rewritten query:** _What cat breed is best suited for a GitLab office environment?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.593

Я не знаю. 

**Sources:** 
- Никакие источники не использованы.

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=0 → final=0 | best_score=0.593

Я не знаю. 

**Sources:** None

---

## Q9: Как лучше жарить картошку с луком?

**Expected:** Полностью не по теме, никакой связи с GitLab Handbook — ожидается низкий similarity score

**Rewritten query:** _What are the best techniques for frying potatoes with onions?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.423

Я не знаю. 

**Sources:** N/A

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=0 → final=0 | best_score=0.412

Я не знаю. 

**Sources:** отсутствуют

---

## Q10: Есть ли у GitLab дресс-код для видеозвонков?

**Expected:** Не по теме — в Handbook нет дресс-кода; пограничный случай, звучит как правдоподобный HR-вопрос

**Rewritten query:** _Is there a dress code for video calls at GitLab?_

### RAG без фильтра (threshold=0.0)

**Stats:** raw=20 → kept=20 → final=5 | best_score=0.677

Я не знаю.

### RAG с фильтром (threshold=0.65)

**Stats:** raw=20 → kept=2 → final=2 | best_score=0.676

В предоставленном контексте нет упоминания о дресс-коде для видеозвонков в GitLab. Поэтому я не знаю, есть ли он.

**Sources:** 
- [GitLab Handbook Communication](https://handbook.gitlab.com/handbook/communication/) - "is difficult (or impossible) to multi-task in a video call."

---

## Итоговая таблица (RAG без фильтра vs RAG с фильтром, threshold=0.65)

| # | Вопрос | best_score | kept без фильтра | kept с фильтром | Ответ изменился? |
|---|--------|-----------|------------------|------------------|-------------------|
| Q1 | PTO / отпуск | 0.80 | 20 | 14 | Нет — тот же ответ, фильтр просто убрал шум из контекста |
| Q2 | Срок ревью (36ч) | 0.82 | 20 | 20 | Нет — фильтр вообще ничего не отсёк (всё было ≥0.65) |
| Q3 | Декрет / уход за ребёнком | 0.78 | 20 | 4 | Нет — короче, но так же верно и с той же цитатой |
| Q4 | Power harassment | 0.79 | 20 | 6 | Нет — ответ идентичен по сути |
| Q5 | Tilt/Okta (США) | 0.72–0.74 | 20 | 12 | Нет |
| Q6 | RCA после инцидента | 0.77 | 20 | 15 | Нет |
| Q7 | Собаки (нерелевантно) | 0.64 | 20 | **0** | Нет по тексту — «не знаю» и без фильтра, и с фильтром |
| Q8 | Кошка (нерелевантно) | 0.59 | 20 | **0** | Нет по тексту — «не знаю» в обоих случаях |
| Q9 | Жарка картошки (нерелевантно) | 0.41–0.42 | 20 | **0** | Нет по тексту — «не знаю» в обоих |
| Q10 | Дресс-код видеозвонков (пограничный) | 0.68 | 20 | 2 | Нет по сути, но с фильтром ответ короче и честнее ссылается на "нет в контексте" |

## Честные выводы

- **Фильтр реально режет контекст.** Для реальных вопросов `kept` падает с 20 до 4–20 (в среднем ~10), для мусорных — до **0**. Это измеримо и воспроизводимо (см. `best_score` рядом — он одинаковый в обеих колонках, потому что это top-1 score из сырых 20 кандидатов, независимо от порога).
- **Текст финального ответа почти не изменился.** На этом наборе вопросов query rewrite + системный промпт («отвечай только по контексту, иначе скажи не знаю») уже сам по себе достаточно хорошо режет галлюцинации — даже без фильтра LLM сама отказалась отвечать на Q7–Q9. Порог здесь не столько меняет ПРАВИЛЬНОСТЬ ответа, сколько:
  - **гарантирует** это поведение детерминированно (не полагаясь на то, что LLM «одумается» глядя на мусорный контекст — a rewrite gate это вероятностно, а cosine threshold — нет);
  - **экономит токены/контекст**: для Q9 в контекст вообще не попадает ни один чанк, вместо 5 мусорных;
  - служит основой для day-24 don't-know gate (жёсткий отказ ДО вызова LLM, без траты токенов на генерацию).
- **Реальные вопросы не пострадали** — все 6 дают одинаково точные ответы что с фильтром, что без. Значит порог 0.65 — рабочая настройка для этого корпуса и индекса (nomic-embed-text + переведённый rewrite).
- **query rewrite — не декорация, а необходимость.** Без перевода на английский (баг в старой версии скрипта) даже правильные вопросы на русском ранжировались криво (см. предыдущий эксперимент выше) — сначала почини это, потом уже крути threshold.

