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

    /// «Символов на токен» — самокалибруется по реальному usage (для локальной оценки до отправки).
    var charsPerToken: Double = TokenEstimator.defaultCharsPerToken
    /// Сколько старых сообщений выкинуто из последнего запроса по токен-бюджету
    /// (демо переполнения: модель их не видит → теряет контекст). 0 — ничего не урезано.
    private(set) var lastTrimmedCount = 0

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
    /// стримит ответ модели по дельтам (onDelta) → возвращает точный usage.
    /// История коммитится только при успехе. Картинка идёт только в текущем сообщении;
    /// в историю пишем текст (или «[фото]»), чтобы не гнать base64 каждый запрос.
    /// tokenBudget (демо переполнения): если задан и контекст его превышает — выкидываем
    /// самые СТАРЫЕ сообщения из отправляемого промпта, пока не влезет. История в UI цела,
    /// но модель старое не видит → реально теряет контекст и забывает. Это и есть «что ломается».
    /// @MainActor — чтобы onDelta и мутации шли на главном потоке (UI безопасно).
    @MainActor
    func respondStreaming(to userInput: String, imageData: Data? = nil, tokenBudget: Int? = nil, onDelta: (String) -> Void) async throws -> TokenUsage? {
        let imageURL = imageData.map { "data:image/jpeg;base64,\($0.base64EncodedString())" }

        let systemReq = ChatMessageRequest(role: .system, text: composedSystem(), imageDataURL: nil)
        let userReq = ChatMessageRequest(role: .user, text: userInput, imageDataURL: imageURL)
        var historyReqs = history.map { ChatMessageRequest(role: $0.role, text: $0.content, imageDataURL: nil) }

        // Демо переполнения: режем самые старые сообщения истории, пока не влезем в бюджет.
        lastTrimmedCount = 0
        if let budget = tokenBudget {
            func estTokens(_ reqs: [ChatMessageRequest]) -> Int {
                TokenEstimator.estimate(reqs.map(\.text).joined(separator: "\n"), charsPerToken: charsPerToken)
            }
            while !historyReqs.isEmpty, estTokens([systemReq] + historyReqs + [userReq]) > budget {
                historyReqs.removeFirst()
                lastTrimmedCount += 1
            }
        }

        let requests: [ChatMessageRequest] = [systemReq] + historyReqs + [userReq]
        let sentChars = requests.reduce(0) { $0 + $1.text.count }

        var answer = ""
        var usage: TokenUsage?
        for try await event in client.completeStreaming(messages: requests, model: model, params: params) {
            switch event {
            case .delta(let chunk):
                answer += chunk
                onDelta(chunk)
            case .usage(let u):
                usage = u
            }
        }
        guard !answer.isEmpty else { throw ProxyAPIError.empty }

        // Калибровка оценки по факту (картинки искажают символ↔токен — пропускаем).
        if imageData == nil, let p = usage?.promptTokens,
           let k = TokenEstimator.calibrate(sentChars: sentChars, promptTokens: p) {
            charsPerToken = k
        }

        let historyText = userInput.isEmpty ? "[фото]" : userInput
        history = history + [
            ChatMessage(role: .user, content: historyText),
            ChatMessage(role: .assistant, content: answer)
        ]
        return usage
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

    /// Что реально уходит в модель: собранный system + окно сообщений.
    var systemContext: String { composedSystem() }
    var contextWindow: [ChatMessage] { history }

    /// Общее самознание агента (как он устроен) — добавляется ВСЕМ агентам.
    private static let selfKnowledge = """
    Как ты устроен (память) — отвечай об этом честно, если спросят:
    - Ты ИИ-агент в приложении AgentChat (на ProxyAPI).
    - В рамках чата ты помнишь весь диалог, и он сохраняется между перезапусками \
    приложения (история на устройстве).
    - О пользователе ты копишь долгие факты — они хранятся и помнятся во ВСЕХ твоих \
    чатах, между сессиями. Новый чат ≠ полная потеря: долгие факты сохраняются.
    - Очень длинный диалог сжимается в краткое содержание, чтобы держать суть.
    Не утверждай, что забываешь всё при новом чате или не хранишь данные — это неверно.
    """

    /// system = персона + самознание + долгие факты + summary старого.
    private func composedSystem() -> String {
        var text = systemPrompt
        text += "\n\n" + Agent.selfKnowledge
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
