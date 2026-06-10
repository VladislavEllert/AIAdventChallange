import Foundation

/// Точный расход токенов за один обмен — из поля `usage` ответа API.
/// promptTokens = ВЕСЬ вход (system + история + текущий запрос — для модели это один промпт),
/// completionTokens = ответ модели, reasoningTokens = скрытое «думанье» (входит в completion).
struct TokenUsage: Hashable {
    let promptTokens: Int
    let completionTokens: Int
    let totalTokens: Int
    var reasoningTokens: Int?

    init(promptTokens: Int, completionTokens: Int, totalTokens: Int, reasoningTokens: Int? = nil) {
        self.promptTokens = promptTokens
        self.completionTokens = completionTokens
        self.totalTokens = totalTokens
        self.reasoningTokens = reasoningTokens
    }
}

extension TokenUsage: Decodable {
    enum CodingKeys: String, CodingKey {
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
        case totalTokens = "total_tokens"
        case completionTokensDetails = "completion_tokens_details"
    }
    private enum DetailKeys: String, CodingKey {
        case reasoningTokens = "reasoning_tokens"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let prompt = try c.decodeIfPresent(Int.self, forKey: .promptTokens) ?? 0
        let completion = try c.decodeIfPresent(Int.self, forKey: .completionTokens) ?? 0
        promptTokens = prompt
        completionTokens = completion
        totalTokens = try c.decodeIfPresent(Int.self, forKey: .totalTokens) ?? (prompt + completion)
        if let details = try? c.nestedContainer(keyedBy: DetailKeys.self, forKey: .completionTokensDetails) {
            reasoningTokens = try details.decodeIfPresent(Int.self, forKey: .reasoningTokens)
        }
    }
}
