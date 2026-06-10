import Foundation
import SwiftData
import Observation

@MainActor
@Observable
final class ChatViewModel {
    /// Сколько последних сообщений держим в окне (остальное → summary).
    private let window = 12

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

    var agentTitle: String { profile.map { "\($0.name) \($0.emoji)" } ?? "" }
    var hasKey: Bool { APIKeyStore.shared.hasKey }
    var currentChatID: UUID? { chat?.id }

    private var selectedModelID: String {
        UserDefaults.standard.string(forKey: "selectedModelID") ?? LLMModel.defaultModel.id
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
        agent?.facts = profile.facts
        agent?.summary = nil
        agent?.setWindow([])
    }

    func open(_ session: ChatSession) {
        chat = session
        let stored = session.sortedMessages
        messages = stored.map { $0.asChatMessage }
        lastExtractCount = messages.count

        agent?.facts = profile?.facts ?? []
        agent?.summary = session.summary
        // в модель уходит только окно последних N; старое — в summary
        let windowMsgs = stored.suffix(window).map {
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

        attachedImage = nil
        errorText = nil
        agent.model = selectedModelID

        messages.append(ChatMessage(role: .user, content: text, imageData: image))
        persist(role: .user, content: text, imageData: image, to: chat, context: context)
        if chat.title == "Новый чат" {
            chat.title = makeTitle(text: text, hasImage: image != nil)
        }
        isLoading = true

        Task {
            do {
                let answer = try await agent.respond(to: text, imageData: image)
                messages.append(ChatMessage(role: .assistant, content: answer))
                persist(role: .assistant, content: answer, imageData: nil, to: chat, context: context)
                await compressIfNeeded(chat: chat)
            } catch {
                errorText = error.localizedDescription
            }
            isLoading = false
            try? context.save()
        }
    }

    /// Если окно переросло лимит — сжать старое в summary, оставить последние N.
    private func compressIfNeeded(chat: ChatSession) async {
        guard let agent, agent.history.count > window else { return }
        let overflow = Array(agent.history.prefix(agent.history.count - window))
        let keep = Array(agent.history.suffix(window))
        guard let newSummary = try? await memory.summarize(previous: chat.summary, overflow: overflow) else { return }
        chat.summary = newSummary
        agent.summary = newSummary
        agent.setWindow(keep)
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

    /// Авто-извлечение фактов при уходе из чата (дешёвая модель, 1 раз на новые сообщения).
    func extractFactsOnLeave() {
        guard let profile, let agent, hasKey, messages.count > lastExtractCount else { return }
        let snapshot = messages
        let known = profile.facts
        lastExtractCount = messages.count
        Task {
            guard let newFacts = try? await memory.extractFacts(messages: snapshot, known: known), !newFacts.isEmpty else { return }
            profile.facts.append(contentsOf: newFacts)
            agent.facts = profile.facts
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

    private func persist(role: Role, content: String, imageData: Data?, to chat: ChatSession, context: ModelContext) {
        let stored = StoredMessage(role: role, content: content, imageData: imageData)
        stored.chat = chat
        chat.messages.append(stored)
        context.insert(stored)
    }

    private func makeTitle(text: String, hasImage: Bool) -> String {
        let base = text.isEmpty && hasImage ? "Фото" : text
        return String(base.prefix(40))
    }
}
