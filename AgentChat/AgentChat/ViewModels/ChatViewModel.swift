import Foundation
import SwiftData
import Observation

@MainActor
@Observable
final class ChatViewModel {
    private var context: ModelContext?
    private(set) var profile: AgentProfile?
    private var agent: Agent?
    private(set) var chat: ChatSession?

    var messages: [ChatMessage] = []
    var input: String = ""
    var attachedImage: Data?
    var isLoading = false
    var errorText: String?

    var agentTitle: String { profile.map { "\($0.name) \($0.emoji)" } ?? "" }
    var hasKey: Bool { APIKeyStore.shared.hasKey }
    var currentChatID: UUID? { chat?.id }

    private var selectedModelID: String {
        UserDefaults.standard.string(forKey: "selectedModelID") ?? LLMModel.defaultModel.id
    }

    var canSend: Bool {
        let hasText = !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        return (hasText || attachedImage != nil) && !isLoading
    }

    /// Привязать хранилище + агента, открыть его последний чат (или новый).
    func attach(_ context: ModelContext, profile: AgentProfile) {
        guard self.profile == nil else { return }
        self.context = context
        self.profile = profile
        self.agent = Agent(profile: profile, model: selectedModelID)

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
        agent?.loadHistory([])
    }

    func open(_ session: ChatSession) {
        chat = session
        let stored = session.sortedMessages
        messages = stored.map { $0.asChatMessage }
        agent?.loadHistory(stored.map {
            ChatMessage(role: $0.role, content: $0.content.isEmpty ? "[фото]" : $0.content)
        })
    }

    /// Чат удалён извне (из списка). Если это текущий — переключиться на другой/новый.
    func chatDeleted(_ id: UUID) {
        guard chat?.id == id else { return }
        if let next = latestChat() {
            open(next)
        } else {
            chat = nil
            messages = []
            agent?.loadHistory([])
            newChat()
        }
    }

    func send() {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        let image = attachedImage
        guard (!text.isEmpty || image != nil), !isLoading else { return }
        guard let context, let agent else { return }
        if chat == nil { newChat() }
        guard let chat else { return }

        input = ""
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
            } catch {
                errorText = error.localizedDescription
            }
            isLoading = false
            try? context.save()
        }
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
