import Foundation

/// Агент — отдельная сущность (не голый вызов API).
/// Владеет личностью (systemPrompt, model, params) и сессионной историей.
/// Логика запрос/ответ инкапсулирована здесь: снаружи зовут `respond(to:)`,
/// а не клиент напрямую.
final class Agent {
    let name: String
    let emoji: String
    let systemPrompt: String
    var model: String
    var params: GenerationParams

    /// Долгая память (факты о юзере) и сжатая выжимка старого — слои контекста.
    var facts: [String] = []
    var summary: String?

    private let client: ProxyAPIClient
    private(set) var history: [ChatMessage] = []

    init(
        name: String,
        emoji: String,
        systemPrompt: String,
        model: String,
        params: GenerationParams,
        client: ProxyAPIClient = ProxyAPIClient()
    ) {
        self.name = name
        self.emoji = emoji
        self.systemPrompt = systemPrompt
        self.model = model
        self.params = params
        self.client = client
    }

    /// Принимает запрос юзера (+опц. фото) → собирает контекст (system + история) →
    /// зовёт LLM → возвращает ответ. История коммитится только при успехе.
    /// Картинка идёт только в текущем сообщении; в историю пишем текст (или «[фото]»),
    /// чтобы не гнать base64 каждый запрос.
    func respond(to userInput: String, imageData: Data? = nil) async throws -> String {
        let imageURL = imageData.map { "data:image/jpeg;base64,\($0.base64EncodedString())" }

        var requests: [ChatMessageRequest] = [ChatMessageRequest(role: .system, text: composedSystem(), imageDataURL: nil)]
        requests += history.map { ChatMessageRequest(role: $0.role, text: $0.content, imageDataURL: nil) }
        requests.append(ChatMessageRequest(role: .user, text: userInput, imageDataURL: imageURL))

        let answer = try await client.complete(messages: requests, model: model, params: params)

        let historyText = userInput.isEmpty ? "[фото]" : userInput
        history = history + [
            ChatMessage(role: .user, content: historyText),
            ChatMessage(role: .assistant, content: answer)
        ]
        return answer
    }

    func resetHistory() {
        history = []
    }

    /// Загрузить историю из сохранённого чата (при переключении чатов).
    func loadHistory(_ messages: [ChatMessage]) {
        history = messages
    }

    /// Заменить окно истории (после сжатия старого в summary).
    func setWindow(_ messages: [ChatMessage]) {
        history = messages
    }

    /// system = персона + долгие факты + summary старого.
    private func composedSystem() -> String {
        var text = systemPrompt
        if !facts.isEmpty {
            text += "\n\nЧто ты помнишь о пользователе:\n" + facts.map { "- \($0)" }.joined(separator: "\n")
        }
        if let summary, !summary.isEmpty {
            text += "\n\nКраткое содержание предыдущей части диалога:\n\(summary)"
        }
        return text
    }
}

extension Agent {
    /// Собрать рантайм-агента из персистентного профиля. Модель берётся из настроек.
    convenience init(profile: AgentProfile, model: String, params: GenerationParams = .bro) {
        self.init(
            name: profile.name,
            emoji: profile.emoji,
            systemPrompt: profile.systemPrompt,
            model: model,
            params: params
        )
    }
}
