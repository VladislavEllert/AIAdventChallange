# RAG Evaluation — Day 25: Task Memory + Multi-turn

Model: `openai/gpt-4o-mini` | Index: fixed | threshold=0.5 | top_k=5 | query_rewrite=ON

---

## Scenario: New employee onboarding

**Sources present:** 9/10 turns (⚠️ PARTIAL)

**Initial goal extracted:** _успешное начало работы в GitLab_

**Final goal:** _успешное начало работы в GitLab_

### Turn 1: I'm starting at GitLab next week. What should I know first?

**RAG:** score=0.707 | sources=❌

**Rewritten:** _What are the essential things I should learn before starting my new job at GitLab next week?_

**Answer:**
I don't know.

---

### Turn 2: What are GitLab's core values?

**RAG:** score=0.745 | sources=✅

**Rewritten:** _What are the fundamental principles and core values that guide GitLab as an organization?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе

**Answer:**
GitLab's six core values are:

1. **🤝 Collaboration**
2. **📈 Results for Customers**
3. **⏱️ Efficiency**
4. **🌐 Diversity, Inclusion & Belonging**
5. **👣 Iteration**
6. **👁️ Transparency**

These values collectively spell the acronym **CREDIT**, which reflects the culture and principles that guide interactions within the company.

**Sources:** 
- https://handbook.gitlab.com/handbook/values/

---

### Turn 3: How does remote communication work at GitLab?

**RAG:** score=0.752 | sources=✅

**Rewritten:** _What are the specific methods and tools utilized for remote communication within GitLab?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab

**Answer:**
At GitLab, clear communication is essential due to its all-remote structure. The company practices asynchronous communication to help everyone stay connected and work more efficiently, given that team members are located in various places around the world. To facilitate effective collaboration, GitLab encourages using tools like Slack instead of relying heavily on email, promoting informal interactions to build social relationships, and ensuring that communications are transparent and aligned with the company's core values. 

Additionally, team members have opportunities to engage with external parties by sharing their expertise, which is also handled with careful consideration for personal data and the company's image.

**Sources:** 
- https://handbook.gitlab.com/handbook/communication/

---

### Turn 4: What is the time-off policy? How many days do I get?

**RAG:** score=0.710 | sources=✅

**Rewritten:** _What are the details of the time-off policy, and how many days of leave or vacation am I entitled to receive?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab

**Answer:**
GitLab has a Flexible Paid Time Off (PTO) policy, which allows team members to use their time off for personal obligations, rest, vacations, or any other necessary time away. The specific number of days you can take varies based on your role, location, and any other applicable benefits or agreements. For detailed information regarding the time-off policy as it pertains to your specific situation or location, it's best to consult the GitLab handbook or your HR representative.

**Sources:** 
- https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/

---

### Turn 5: Can I take parental leave?

**RAG:** score=0.746 | sources=✅

**Rewritten:** _Am I eligible to take parental leave? What are the requirements and policies regarding parental leave?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab

**Answer:**
Yes, you can take parental leave at GitLab if you are an active team member who becomes a parent through childbirth or adoption. GitLab offers a 16-week paid parental leave policy that is available to all eligible employees, regardless of gender. You should check specific details or statutory benefits applicable to your location, as they may vary.

**Sources:**
- https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/

---

### Turn 6: I'm a senior engineer. What's the code review process?

**RAG:** score=0.771 | sources=✅

**Rewritten:** _What are the steps and best practices involved in the code review process for software engineering?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab; пользователь спрашивал про политику отпусков в GitLab

**Answer:**
As a senior engineer at GitLab, the code review process involves several key steps:

1. **Mandatory Code Reviews**: Every merge request (MR) requires a code review as per GitLab's policies. Familiarize yourself with the [Code Review Guidelines](https://docs.gitlab.com/ee/development/code_review.html) to understand the expectations and procedures.

2. **Review Responsibilities**: Identify who needs to review, approve, and merge your merge request, as well as the SLOs (Service Level Objectives) for review response times. Ensure that you communicate any changes or feedback with the reviewers promptly.

3. **Reviewer Values**: As a reviewer, strive to maintain the quality and maintainability of the codebase while fostering a supportive and respectful environment. Balance iteration with quality concerns, ensuring that the changes contribute positively to the user experience and reliability.

4. **Communication and Feedback**: If you cannot review an MR within the designated time frame, inform the author as soon as possible (preferably within 36 hours) and assist them in finding another reviewer. Use comments and status emojis to communicate effectively.

5. **Constructive Feedback**: Provide constructive feedback focused on maintaining high-quality standards, and be open to discussions that may arise during the review process.

Following these steps will help ensure an efficient and collaborative code review process at GitLab.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/code-review/
- https://handbook.gitlab.com/handbook/engineering/workflow/reviewer-values/

---

### Turn 7: How long should a code review typically take?

**RAG:** score=0.694 | sources=✅

**Rewritten:** _What is the typical duration for a code review process?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab; пользователь спрашивал про политику отпусков в GitLab

**Answer:**
The typical time frame for a code review at GitLab, known as the review-response SLO (Service Level Objective), emphasizes that reviewers should respond to a merge request within 36 hours of first receiving the review request. This timeframe helps ensure that authors are not blocked in their work and can continue making progress as quickly as possible.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/code-review/

---

### Turn 8: What happens if I disagree with a reviewer's feedback?

**RAG:** score=0.673 | sources=✅

**Rewritten:** _What are the potential outcomes or consequences of not agreeing with the feedback provided by a reviewer?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab; пользователь спрашивал про политику отпусков в GitLab

**Answer:**
If you disagree with a reviewer's feedback at GitLab, it's important to approach the situation thoughtfully and constructively. You can express your concerns and engage in a discussion with the reviewer. Maintain a respectful tone and focus on understanding their perspective while clearly articulating your viewpoint.

The process encourages open communication and collaboration, allowing for differences in opinion. If necessary, you may also seek input from other team members or senior engineers to help mediate the discussion or provide additional insights.

Ultimately, once a decision has been made, all team members are expected to commit to executing that decision, even if they disagreed initially. Past decisions can be questioned, but during the execution of a project, collaboration and commitment are crucial.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/reviewer-values/
- https://handbook.gitlab.com/handbook/values/

---

### Turn 9: Is there a preference for async vs sync communication?

**RAG:** score=0.666 | sources=✅

**Rewritten:** _What are the advantages and disadvantages of asynchronous communication compared to synchronous communication, and is there a preference for one over the other in different contexts?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab; пользователь спрашивал про политику отпусков в GitLab

**Answer:**
Yes, GitLab emphasizes the importance of asynchronous (async) communication over synchronous (sync) communication for various reasons. Async communication allows for more inclusive conversations, as anyone can contribute at any time and discussions can proceed at a flexible pace. It is particularly advantageous for remote teams, as it accommodates different time zones and reduces the need for everyone to be present at the same time.

Synchronous communication, such as video calls, can be limiting in terms of time and participation, whereas async conversations can start and stop as necessary, allowing for a more organized and thoughtful exchange of ideas.

GitLab encourages clear communication practices that help teams stay connected and work efficiently, highlighting that async communication is often preferable in many contexts.

**Sources:**
- https://handbook.gitlab.com/handbook/communication/

---

### Turn 10: Summarize the key things I told you I need to know as a new GitLab employee

**RAG:** score=0.706 | sources=✅

**Rewritten:** _What are the essential pieces of information and key resources that I should be aware of as a new employee at GitLab?_

**Task state:**
- Goal: успешное начало работы в GitLab
- Clarified: пользователь начинает работать в GitLab на следующей неделе; спросил про основные ценности GitLab; пользователь спрашивал про политику отпусков в GitLab

**Answer:**
As a new employee at GitLab, here are the key aspects you need to know:

1. **Core Values**: Familiarize yourself with GitLab's core values which underpin how the company operates and interacts with its employees and customers.

2. **Code Review Process**: Understand that every merge request requires a code review, which should be responded to within 36 hours. Engage in constructive dialogue if you disagree with feedback.

3. **Asynchronous Communication**: GitLab prefers asynchronous communication over synchronous methods to accommodate team members in different time zones and foster inclusive discussions.

4. **Leave Policies**: Be aware of GitLab’s leave policies, including vacation and parental leave, to understand your entitlements and the processes involved.

5. **Focus on Security**: Recognize the importance of security within GitLab's operations and how it relates to the product and customer assurance.

6. **People Group Support**: Utilize available resources from the People Group to enhance your career and experience within the company.

7. **Emphasis on Collaboration**: GitLab encourages collaborative practices that align with its mission, valuing contributions that lead to effective teamwork and innovation.

These aspects will help you integrate successfully into your role at GitLab and understand the company culture.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/code-review/
- https://handbook.gitlab.com/handbook/communication/
- https://handbook.gitlab.com/handbook/people-group/
- https://handbook.gitlab.com/handbook/security/

---

## Scenario: Engineering career growth

**Sources present:** 7/10 turns (⚠️ PARTIAL)

**Initial goal extracted:** _развивать карьеру в GitLab_

**Final goal:** _развивать карьеру в GitLab_

### Turn 1: I'm a mid-level engineer at GitLab and I want to grow my career here. Explain GitLab's software development workflow first

**RAG:** score=0.761 | sources=✅

**Rewritten:** _As a mid-level engineer at GitLab seeking to advance your career within the company, could you provide a detailed explanation of the software development workflow utilized at GitLab?_

**Answer:**
GitLab's software development workflow is primarily based on the GitLab Flow, which integrates both continuous integration and deployment practices along with issue tracking. Here are the key points of the workflow:

1. **Collaboration**: Teams typically consist of backend engineers, frontend engineers, product designers, and product managers who share the responsibility for shipping issues in a planned release.

2. **Issue Management**: Development begins with issues that are logged and prioritized based on customer needs and business strategy. Each team collaborates to determine the technical implementation (the "How") and scheduling (the "When") of releases.

3. **Code Review**: There are specific rules around code review, ensuring quality and alignment with GitLab's standards before any code is merged into the main branch.

4. **Reverting Changes**: If necessary, there are procedures in place for reverting merge requests to maintain the integrity of the codebase.

5. **Continuous Feedback and Improvement**: As development progresses, teams are encouraged to continuously communicate and reassess their ability to deliver features on time, addressing any potential delays proactively.

This structured yet flexible approach allows for efficient collaboration, accountability, and responsiveness to feedback, ensuring that GitLab products continue to meet user needs effectively.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/
- https://handbook.gitlab.com/handbook/engineering/

---

### Turn 2: How are merge requests handled and reviewed?

**RAG:** score=0.715 | sources=✅

**Rewritten:** _What are the procedures and best practices for managing and reviewing merge requests in software development?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
Merge requests in GitLab are handled through a structured code review process. Here are the key aspects:

1. **Mandatory Code Reviews**: Every merge request must undergo a code review before it can be merged. This ensures that the code adheres to GitLab’s quality standards.

2. **Review Assignments**: The guidelines specify who needs to review, approve, and eventually merge the merge request. Assignments are typically made based on expertise and availability.

3. **Review Response Time**: Reviewers are expected to respond within certain service level objectives (SLOs). If a reviewer is unable to provide feedback in a timely manner, they should inform the author and help find another available reviewer to prevent any blocks.

4. **Feedback and Communication**: Reviewers communicate feedback through comments in the merge request and can indicate their review status using various emojis. This helps maintain clarity about where a review stands.

5. **Auto-Merge Functionality**: Once a merge request has been approved and the relevant reviews have occurred, maintainers can use the auto-merge feature to streamline the integration of the changes into the main branch.

Overall, this process emphasizes collaboration, prompt communication, and adherence to quality standards to ensure successful integration of code changes.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/code-review/
- https://handbook.gitlab.com/handbook/engineering/workflow/

---

### Turn 3: What are the engineering management principles at GitLab?

**RAG:** score=0.782 | sources=❌

**Rewritten:** _What are the key engineering management principles used at GitLab?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
I don't know.

---

### Turn 4: How do performance reviews work for engineers?

**RAG:** score=0.669 | sources=❌

**Rewritten:** _What is the process and methodology of performance evaluations for engineering professionals?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
I don't know.

---

### Turn 5: What are the criteria for promotion to senior engineer?

**RAG:** score=0.711 | sources=✅

**Rewritten:** _What are the specific requirements and criteria for advancing to the position of Senior Engineer?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
The criteria for promotion to a Senior engineer at GitLab include:

1. **Maintainership**: Engineers moving into the Senior role are expected to have already become maintainers prior to their promotion. This means they should have demonstrated the ability to review and merge code effectively.

2. **Experience and Expertise**: They should have a sufficient level of experience and expertise that aligns with the responsibilities and expectations of a Senior engineer.

Overall, the emphasis is on demonstrating the necessary skills and responsibilities through maintainership before being eligible for promotion.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/workflow/code-review/

---

### Turn 6: How does GitLab handle underperforming team members?

**RAG:** score=0.714 | sources=❌

**Rewritten:** _What strategies and processes does GitLab implement to manage and address the performance issues of team members who are not meeting expectations?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
I don't know.

---

### Turn 7: What is expected from an engineering manager vs individual contributor?

**RAG:** score=0.645 | sources=✅

**Rewritten:** _What are the typical responsibilities and expectations of an engineering manager compared to those of an individual contributor in a technical team?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
An engineering manager at GitLab is expected to take on the following responsibilities compared to an individual contributor:

1. **Team Leadership**: Engineering managers guide and support their teams, fostering a collaborative environment and ensuring that team members are aligned with the overall goals.

2. **Strategic Direction**: They contribute to the strategic planning and execution of engineering goals, working closely with other departments and stakeholders to prioritize and define the technical roadmap.

3. **Performance Management**: Managers are responsible for assessing team performance, providing feedback, and facilitating development opportunities for their team members.

4. **Communication**: They are expected to facilitate communication within the team and across the organization, ensuring that everyone is informed and engaged.

In contrast, an individual contributor focuses more on executing their specific tasks, such as coding, reviewing code, and delivering features or products as part of their designated role within the team.

**Sources:**
- https://handbook.gitlab.com/handbook/engineering/

---

### Turn 8: How does GitLab approach psychological safety and inclusion?

**RAG:** score=0.758 | sources=✅

**Rewritten:** _What strategies and practices does GitLab implement to foster psychological safety and promote inclusion within its organization?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
GitLab approaches psychological safety and inclusion by fostering a safe community where all team members feel secure in expressing themselves. The organization emphasizes that:

1. **Non-Discrimination**: GitLab does not tolerate abuse, harassment, exclusion, discrimination, or retaliation within its community. This creates an environment where individuals can feel safe and valued.

2. **Respectful Communication**: Employees are encouraged not to make jokes or unfriendly remarks about personal characteristics. Such respect is crucial for maintaining a positive culture.

3. **Supportive Environment**: Managers are advised to facilitate environments that promote psychological safety, including providing reasonable accommodations that help team members perform their roles effectively.

Overall, GitLab prioritizes creating an inclusive workplace where all employees can thrive without fear of negative consequences based on their identity.

**Sources:**
- https://handbook.gitlab.com/handbook/values/
- https://handbook.gitlab.com/handbook/company/culture/inclusion/

---

### Turn 9: What mentorship or learning opportunities does GitLab offer?

**RAG:** score=0.807 | sources=✅

**Rewritten:** _What mentorship programs or educational opportunities does GitLab provide for individuals seeking to enhance their skills and knowledge?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
GitLab offers several mentorship and learning opportunities, including:

1. **Women's TMRG Mentorship Group**: This group allows individuals to either be a mentor, practicing leadership, or to get paired with a leader from whom they can learn.

2. **Shadow Program**: GitLab encourages team members to explore opportunities to join a job shadow program, which allows them to learn from others in different roles.

3. **Leadership Transition Skills**: GitLab provides resources to explore the skills needed to successfully transition from an individual contributor role to a managerial position.

These initiatives are designed to support career development and facilitate growth within the organization.

**Sources:**
- https://handbook.gitlab.com/handbook/leadership/
- https://handbook.gitlab.com/handbook/people-group/learning-and-development/growth-and-development/

---

### Turn 10: Based on what you've told me, what should I focus on to grow my career at GitLab?

**RAG:** score=0.761 | sources=✅

**Rewritten:** _What specific areas or skills should I concentrate on to enhance my career development opportunities at GitLab?_

**Task state:**
- Goal: развивать карьеру в GitLab
- Clarified: пользователь - инженер среднего уровня в GitLab; пользователь хочет развивать карьеру в GitLab; пользователь попросил объяснить рабочий процесс разработки ПО в GitLab

**Answer:**
To grow your career at GitLab, you should focus on the following areas:

1. **Development of Technical Skills**: Leverage the competencies framework provided by GitLab to enhance your skills relevant to your current role. This framework can help you understand what knowledge and behaviors are necessary for effective performance.

2. **Mentorship Opportunities**: Participate in programs such as the Women's TMRG mentorship group to either mentor others or find a mentor who can help guide your career decisions and growth.

3. **Job Shadowing**: Engage in the Shadow program to observe and learn from colleagues in different roles. This can help you gain insights into other positions and possibly prepare for future opportunities.

4. **Transitioning to Management**: If you're interested in moving into a managerial role, explore the skills needed to transition successfully from an individual contributor to a manager.

5. **Engage in Continuous Learning**: Take advantage of any formal coaching programs that may be introduced, as well as any ongoing learning and development resources provided by GitLab.

By focusing on these areas, you can enhance your career growth and align your development with GitLab's goals.

**Sources:**
- https://handbook.gitlab.com/handbook/leadership/
- https://handbook.gitlab.com/handbook/people-group/learning-and-development/growth-and-development/
- https://handbook.gitlab.com/handbook/people-group/competencies/

---

