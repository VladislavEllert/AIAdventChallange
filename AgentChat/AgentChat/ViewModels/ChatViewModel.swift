import Foundation
import SwiftData
import Observation

@MainActor
@Observable
final class ChatViewModel {
    /// Сжатие истории (summary) включено? Выкл → шлём ВСЮ историю целиком (без окна/summary),
    /// для сравнения качества и токенов без сжатия.
    var summaryEnabled: Bool { UserDefaults.standard.object(forKey: "summaryEnabled") as? Bool ?? true }

    /// Сколько последних сообщений держим в окне (остальное → summary).
    /// Демо-крутилка: можно уменьшить, чтобы вытеснение старого контекста было видно быстро.
    /// Сжатие выкл → окно не ограничено (вся история).
    private var window: Int {
        guard summaryEnabled else { return .max }
        let v = UserDefaults.standard.integer(forKey: "demoWindowSize")
        return v >= 2 ? v : 12
    }

    private var context: ModelContext?
    private(set) var profile: AgentProfile?
    private var agent: Agent?
    private(set) var chat: ChatSession?
    private let memory = MemoryService()
    private var lastExtractCount = 0

    var messages: [ChatMessage] = []
    var attachedImage: Data?
    var isLoading = false
    var errorText: String?

    /// id растущего ответа (стриминг). nil — стрима нет.
    var streamingID: UUID?
    /// prompt_tokens последнего реального запроса (для метра контекста).
    var lastPromptTokens = 0
    /// Сколько старых сообщений выкинуто из последнего запроса (демо переполнения).
    var trimmedCount = 0
    /// Идёт компактация контекста (сжатие старого в summary).
    var isCompacting = false

    var agentTitle: String { profile.map { "\($0.name) \($0.emoji)" } ?? "" }
    var hasKey: Bool { APIKeyStore.shared.hasKey }
    var currentChatID: UUID? { chat?.id }

    private var selectedModelID: String {
        UserDefaults.standard.string(forKey: "selectedModelID") ?? LLMModel.defaultModel.id
    }

    // MARK: - Демо-крутилки (учебные) и лимит контекста

    var demoLimitEnabled: Bool { UserDefaults.standard.bool(forKey: "demoLimitEnabled") }
    private var demoLimitValue: Int {
        let v = UserDefaults.standard.integer(forKey: "demoLimitValue")
        return v > 0 ? v : 2000
    }
    /// Эффективный лимит окна: демо-лимит (если включён) или реальный лимит модели.
    var effectiveContextLimit: Int {
        demoLimitEnabled ? demoLimitValue : LLMModel.by(id: selectedModelID).contextLimit
    }
    var windowSize: Int { window }

    // MARK: - Живые агрегаты по чату (токены и ₽)

    /// Сумма токенов всех обменов чата.
    var sessionTokens: Int { messages.compactMap { $0.usage?.totalTokens }.reduce(0, +) }
    /// Стоимость всех обменов чата в рублях (по модели, которая реально отвечала).
    var sessionCostRub: Double {
        messages.reduce(0) { acc, m in
            guard let u = m.usage else { return acc }
            return acc + LLMModel.by(id: m.modelID ?? selectedModelID).cost(u)
        }
    }
    /// Заполнение контекста: последний prompt против эффективного лимита (0…1).
    var contextFill: Double {
        guard effectiveContextLimit > 0 else { return 0 }
        return min(1, Double(lastPromptTokens) / Double(effectiveContextLimit))
    }
    /// Реальное число сообщений в окне, что уходит в модель (после токен-сжатия/обрезки).
    var windowMessageCount: Int { agent?.contextWindow.count ?? 0 }
    /// Сколько сообщений диалога уже вне окна (сжаты в summary). Системные плашки не считаем.
    var compressedMessageCount: Int {
        let dialogue = messages.filter { $0.role != .system }.count
        return max(0, dialogue - windowMessageCount)
    }
    var hasSummary: Bool { (chat?.summary?.isEmpty == false) }
    /// Текущая сжатая выжимка чата (что сейчас «помнится» вместо старых сообщений).
    var currentSummary: String? { chat?.summary }

    // Разбивка по направлениям + среднее время (для листа «Статистика чата»).
    var sessionPromptTokens: Int { messages.compactMap { $0.usage?.promptTokens }.reduce(0, +) }
    var sessionCompletionTokens: Int { messages.compactMap { $0.usage?.completionTokens }.reduce(0, +) }
    var sessionReasoningTokens: Int { messages.compactMap { $0.usage?.reasoningTokens }.reduce(0, +) }
    var answeredCount: Int { messages.filter { $0.usage != nil }.count }
    var avgResponseTime: Double {
        let times = messages.compactMap { $0.responseTime }
        return times.isEmpty ? 0 : times.reduce(0, +) / Double(times.count)
    }

    /// Привязать хранилище + агента, открыть его последний чат (или новый).
    func attach(_ context: ModelContext, profile: AgentProfile) {
        guard self.profile == nil else { return }
        self.context = context
        self.profile = profile
        self.agent = Agent(profile: profile, model: selectedModelID)
        self.agent?.facts = profile.facts

        if let last = latestChat() {
            open(last)
        } else {
            newChat()
        }
    }

    func newChat() {
        guard let context, let profile else { return }
        if let chat, chat.messages.isEmpty { return }  // не плодим пустые
        let session = ChatSession(agentID: profile.id)
        context.insert(session)
        chat = session
        messages = []
        lastExtractCount = 0
        lastPromptTokens = 0
        trimmedCount = 0
        streamingID = nil
        agent?.facts = profile.facts
        agent?.summary = nil
        agent?.setWindow([])
    }

    func open(_ session: ChatSession) {
        chat = session
        streamingID = nil
        trimmedCount = 0
        let stored = session.sortedMessages
        messages = stored.map { $0.asChatMessage }
        lastExtractCount = messages.count
        lastPromptTokens = stored.last(where: { $0.role == .assistant })?.promptTokens ?? 0

        agent?.facts = profile?.facts ?? []
        agent?.summary = summaryEnabled ? session.summary : nil
        // в модель уходит только окно последних N; старое — в summary.
        // Системные плашки (сжатие) — только для UI, в контекст модели НЕ кладём.
        let windowMsgs = stored.filter { $0.role != .system }.suffix(window).map {
            ChatMessage(role: $0.role, content: $0.content.isEmpty ? "[фото]" : $0.content)
        }
        agent?.setWindow(Array(windowMsgs))
    }

    /// Чат удалён извне (из списка). Если это текущий — переключиться на другой/новый.
    func chatDeleted(_ id: UUID) {
        guard chat?.id == id else { return }
        if let next = latestChat() {
            open(next)
        } else {
            chat = nil
            messages = []
            agent?.setWindow([])
            newChat()
        }
    }

    func send(text rawText: String) {
        let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        let image = attachedImage
        guard (!text.isEmpty || image != nil), !isLoading else { return }
        guard let context, let agent else { return }
        if chat == nil { newChat() }
        guard let chat else { return }
        agent.model = selectedModelID

        // Ручная команда «сжать контекст» — не обычное сообщение, а запуск компактации.
        if image == nil, isCompactCommand(text) {
            Task { await compactNow(auto: false) }
            return
        }

        attachedImage = nil
        errorText = nil
        // Демо переполнения: лимит окна = токен-бюджет. Превысили → старые сообщения
        // выкидываются из промпта (страховка, чтобы не упереться в стену) → модель забывает.
        let budget: Int? = (summaryEnabled && demoLimitEnabled) ? effectiveContextLimit : nil

        messages.append(ChatMessage(role: .user, content: text, imageData: image))
        persist(role: .user, content: text, imageData: image, to: chat, context: context)
        if chat.title == "Новый чат" {
            chat.title = makeTitle(text: text, hasImage: image != nil)
        }
        isLoading = true
        let modelID = agent.model
        let start = Date()

        Task {
            // Авто-компактация при подходе к лимиту: сжать старое окно → токены падают.
            // Если сработала — окно уже урезано, второй (message-count) проход не нужен.
            let didCompact = (summaryEnabled && estimatedContextTokens(plus: text) >= compactThreshold)
                ? await compactNow(auto: true)
                : false

            // Плейсхолдер ответа — стриминг будет дописывать его content по дельтам.
            let placeholder = ChatMessage(role: .assistant, content: "")
            let placeholderID = placeholder.id
            messages.append(placeholder)
            streamingID = placeholderID
            do {
                let usage = try await agent.respondStreaming(to: text, imageData: image, tokenBudget: budget) { [weak self] delta in
                    guard let self, let idx = self.messages.firstIndex(where: { $0.id == placeholderID }) else { return }
                    self.messages[idx].content += delta
                }
                trimmedCount = agent.lastTrimmedCount
                let elapsed = Date().timeIntervalSince(start)
                let finalText = messages.first(where: { $0.id == placeholderID })?.content ?? ""
                if let idx = messages.firstIndex(where: { $0.id == placeholderID }) {
                    messages[idx].usage = usage
                    messages[idx].responseTime = elapsed
                    messages[idx].modelID = modelID
                }
                if let usage { lastPromptTokens = usage.promptTokens }
                persist(role: .assistant, content: finalText, imageData: nil, to: chat, context: context,
                        usage: usage, responseTime: elapsed, modelID: modelID)
                if summaryEnabled, !didCompact { await compressIfNeeded(chat: chat) }
            } catch {
                messages.removeAll { $0.id == placeholderID }   // убрать незавершённый ответ
                errorText = friendlyError(error)
            }
            streamingID = nil
            isLoading = false
            try? context.save()
        }
    }

    /// Понятное сообщение об ошибке. Отдельно ловим переполнение контекста (что и ломается).
    private func friendlyError(_ error: Error) -> String {
        if case let ProxyAPIError.http(status, body) = error {
            let low = body.lowercased()
            let overflow = low.contains("context") || low.contains("maximum") || low.contains("too many tokens") || low.contains("token limit")
            if status == 400, overflow {
                return "⚠️ Контекст превысил лимит модели (HTTP 400) — это и ломается при переполнении: модель отказывается обрабатывать запрос. \(body)"
            }
        }
        return error.localizedDescription
    }

    /// Если окно переросло лимит по числу сообщений — сжать старое в summary,
    /// оставить последние N. Теперь тоже выводит плашку (раньше делал это молча).
    private func compressIfNeeded(chat: ChatSession) async {
        guard let agent, agent.history.count > window else { return }
        let overflow = Array(agent.history.prefix(agent.history.count - window))
        let keep = Array(agent.history.suffix(window))
        let note = ChatMessage(role: .system, content: "Сжимаю контекст…")
        let noteID = note.id
        messages.append(note)
        let prevSummary = chat.summary
        guard let newSummary = try? await memory.summarize(previous: prevSummary, overflow: overflow, maxWords: compressionLevel.summaryWords) else {
            messages.removeAll { $0.id == noteID }
            return
        }
        chat.summary = newSummary
        agent.summary = newSummary
        agent.setWindow(keep)
        let noteText = compactionNoteText(messagesFolded: overflow.count, prevSummary: prevSummary, newSummary: newSummary, tag: "(окно)")
        if let idx = messages.firstIndex(where: { $0.id == noteID }) {
            messages[idx].content = noteText
        }
        persistSystemNote(noteText, to: chat)
    }

    /// Сохранить системную плашку (сжатие) в SQLite, чтобы она пережила перезапуск.
    private func persistSystemNote(_ text: String, to chat: ChatSession) {
        guard let context else { return }
        persist(role: .system, content: text, imageData: nil, to: chat, context: context)
        try? context.save()
    }

    private func wordCount(_ s: String) -> Int {
        s.split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" }).count
    }

    /// Текст плашки сжатия. Показывает и сворачивание сообщений, и ПЕРЕСБОРКУ самого
    /// summary (старый summary + новое → новый, в лимит слов) — было→стало слов.
    private func compactionNoteText(messagesFolded: Int, prevSummary: String?, newSummary: String, tag: String) -> String {
        let now = wordCount(newSummary)
        if let prev = prevSummary, !prev.isEmpty {
            return "Контекст сжат: \(messagesFolded) сообщ. + summary пересобран \(wordCount(prev))→\(now) слов \(tag)"
        }
        return "Контекст сжат: \(messagesFolded) сообщ. → новый summary (\(now) слов) \(tag)"
    }

    // MARK: - Компактация контекста (как авто-compact в Claude Code)

    /// Порог запуска авто-компактации: ~85% эффективного лимита окна.
    private var compactThreshold: Int { Int(Double(effectiveContextLimit) * 0.85) }

    /// Грубая оценка токенов контекста (system + окно + опц. следующий текст).
    private func estimatedContextTokens(plus text: String = "") -> Int {
        guard let agent else { return 0 }
        let ctx = agent.systemContext + "\n"
            + agent.contextWindow.map(\.content).joined(separator: "\n")
            + (text.isEmpty ? "" : "\n" + text)
        return TokenEstimator.estimate(ctx, charsPerToken: agent.charsPerToken)
    }

    /// Степень компактации из настроек (сколько свежего окна оставляем).
    private var compressionLevel: CompressionLevel {
        CompressionLevel(rawValue: UserDefaults.standard.string(forKey: "compressionLevel") ?? "") ?? .default
    }

    /// Текст юзера — это команда «сжать контекст»?
    private func isCompactCommand(_ text: String) -> Bool {
        let t = text.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if t == "/compact" || t == "compact" { return true }
        return t.contains("сжать контекст") || t.contains("сожми контекст")
            || t.contains("компресс контекст") || t.contains("компрессия контекст")
            || t.contains("сжать контекс")  // частая опечатка распознавания
    }

    /// Сжать старую половину окна в summary → токены контекста падают (видно в чате).
    /// auto=true — вызвано автоматически у лимита; false — вручную (кнопка/команда).
    @discardableResult
    func compactNow(auto: Bool) async -> Bool {
        guard let agent, let chat, hasKey, !isCompacting, summaryEnabled else { return false }
        if !auto, isLoading { return false }   // вручную — не лезть в активный стрим
        let win = agent.contextWindow
        let note = ChatMessage(role: .system, content: "Сжимаю контекст…")
        let noteID = note.id

        guard win.count >= 2 else {
            messages.append(ChatMessage(role: .system, content: "Нечего сжимать — контекст маленький"))
            return false
        }

        isCompacting = true
        messages.append(note)
        // Оставляем свежие keepCount сообщений, старое начало — в summary.
        let keepCount = min(win.count - 1, max(1, Int((Double(win.count) * compressionLevel.keepFraction).rounded())))
        let keep = Array(win.suffix(keepCount))
        let toCompact = Array(win.prefix(win.count - keepCount))

        let prevSummary = chat.summary
        let newSummary = try? await memory.summarize(previous: prevSummary, overflow: toCompact, maxWords: compressionLevel.summaryWords)
        if let newSummary {
            chat.summary = newSummary
            agent.summary = newSummary
            agent.setWindow(keep)
            trimmedCount = 0
            try? context?.save()
        }
        let noteText = newSummary.map {
            compactionNoteText(messagesFolded: toCompact.count, prevSummary: prevSummary, newSummary: $0, tag: auto ? "(авто)" : "(вручную)")
        } ?? "Не удалось сжать контекст"
        if let idx = messages.firstIndex(where: { $0.id == noteID }) {
            messages[idx].content = noteText
        }
        if newSummary != nil { persistSystemNote(noteText, to: chat) }
        isCompacting = false
        return newSummary != nil
    }

    /// Ручная долгая память: положить факт в копилку агента.
    func remember(_ text: String) {
        guard let profile else { return }
        let fact = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !fact.isEmpty else { return }
        guard !profile.facts.contains(where: { $0.lowercased() == fact.lowercased() }) else { return }
        profile.facts.append(fact)
        agent?.facts = profile.facts
        try? context?.save()
    }

    /// Авто-память включена? (можно выключить для чистого демо переполнения).
    private var autoMemoryEnabled: Bool {
        UserDefaults.standard.object(forKey: "autoMemoryEnabled") as? Bool ?? true
    }

    /// Авто-извлечение фактов при уходе из чата (дешёвая модель, 1 раз на новые сообщения).
    func extractFactsOnLeave() {
        guard autoMemoryEnabled else { return }
        guard let profile, let agent, hasKey, messages.count > lastExtractCount else { return }
        let snapshot = messages
        let known = profile.facts
        lastExtractCount = messages.count
        Task {
            // обновлённый ПОЛНЫЙ список: новое добавит, изменившееся заменит, дубли смёржит
            guard let updated = try? await memory.updatedFacts(known: known, messages: snapshot) else { return }
            profile.facts = updated
            agent.facts = updated
            try? context?.save()
        }
    }

    /// JSON-снимок: что уходит в модель (system + окно) + хранимое.
    func exportJSON() -> String {
        guard let profile, let agent else { return "{}" }
        return memory.exportJSON(
            agentName: "\(profile.name) \(profile.emoji)",
            model: agent.model,
            system: agent.systemContext,
            window: agent.contextWindow,
            facts: profile.facts,
            summary: chat?.summary,
            fullHistory: messages
        )
    }

    private func latestChat() -> ChatSession? {
        guard let context, let profile else { return nil }
        let agentID: UUID? = profile.id
        var descriptor = FetchDescriptor<ChatSession>(
            predicate: #Predicate { $0.agentID == agentID },
            sortBy: [SortDescriptor(\.createdAt, order: .reverse)]
        )
        descriptor.fetchLimit = 1
        return try? context.fetch(descriptor).first
    }

    private func persist(role: Role, content: String, imageData: Data?, to chat: ChatSession, context: ModelContext,
                         usage: TokenUsage? = nil, responseTime: Double? = nil, modelID: String? = nil) {
        let stored = StoredMessage(role: role, content: content, imageData: imageData,
                                   usage: usage, responseTime: responseTime, modelID: modelID)
        stored.chat = chat
        chat.messages.append(stored)
        context.insert(stored)
    }

    private func makeTitle(text: String, hasImage: Bool) -> String {
        let base = text.isEmpty && hasImage ? "Фото" : text
        return String(base.prefix(40))
    }
}
