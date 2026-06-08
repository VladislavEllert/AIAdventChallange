import Foundation

/// Сообщение для запроса. content кодируется либо строкой (текст),
/// либо массивом частей (текст + картинка) — OpenAI vision-формат.
struct ChatMessageRequest: Encodable {
    let role: Role
    let text: String
    let imageDataURL: String?

    enum CodingKeys: String, CodingKey { case role, content }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(role, forKey: .role)
        if let url = imageDataURL {
            var parts: [ContentPart] = []
            if !text.isEmpty { parts.append(.text(text)) }
            parts.append(.image(url))
            try c.encode(parts, forKey: .content)
        } else {
            try c.encode(text, forKey: .content)
        }
    }
}

private enum ContentPart: Encodable {
    case text(String)
    case image(String)

    enum Keys: String, CodingKey { case type, text, image_url }
    struct ImageURL: Encodable { let url: String }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Keys.self)
        switch self {
        case .text(let t):
            try c.encode("text", forKey: .type)
            try c.encode(t, forKey: .text)
        case .image(let url):
            try c.encode("image_url", forKey: .type)
            try c.encode(ImageURL(url: url), forKey: .image_url)
        }
    }
}

private struct ChatCompletionRequest: Encodable {
    let model: String
    let messages: [ChatMessageRequest]
    let temperature: Double?
    let max_tokens: Int

    enum CodingKeys: String, CodingKey { case model, messages, temperature, max_tokens }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(model, forKey: .model)
        try c.encode(messages, forKey: .messages)
        try c.encode(max_tokens, forKey: .max_tokens)
        if let temperature { try c.encode(temperature, forKey: .temperature) }
    }
}

private struct ChatCompletionResponse: Decodable {
    struct Choice: Decodable {
        struct Message: Decodable { let content: String }
        let message: Message
    }
    let choices: [Choice]
}

enum ProxyAPIError: LocalizedError {
    case missingKey
    case invalidResponse
    case http(status: Int, body: String)
    case empty

    var errorDescription: String? {
        switch self {
        case .missingKey:
            return "API-ключ не задан. Открой настройки и вставь ключ ProxyAPI."
        case .invalidResponse:
            return "Некорректный ответ сервера."
        case .http(let status, let body):
            return "Ошибка API (\(status)): \(body)"
        case .empty:
            return "Пустой ответ модели."
        }
    }
}

/// Тупой транспорт. Знает только: messages + params → текст ответа.
/// Про агентов ничего не знает.
struct ProxyAPIClient {
    private let baseURL = URL(string: "https://openai.api.proxyapi.ru/v1")!
    private let apiKey: () -> String?

    init(apiKey: @escaping () -> String? = { APIKeyStore.shared.key }) {
        self.apiKey = apiKey
    }

    func complete(messages: [ChatMessageRequest], model: String, params: GenerationParams) async throws -> String {
        guard let key = apiKey(), !key.isEmpty else { throw ProxyAPIError.missingKey }

        var request = URLRequest(url: baseURL.appending(path: "chat/completions"))
        request.httpMethod = "POST"
        request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let supportsTemperature = LLMModel.by(id: model).supportsTemperature
        request.httpBody = try JSONEncoder().encode(
            ChatCompletionRequest(
                model: model,
                messages: messages,
                temperature: supportsTemperature ? params.temperature : nil,
                max_tokens: params.maxTokens
            )
        )

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ProxyAPIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw ProxyAPIError.http(status: http.statusCode, body: String(data: data, encoding: .utf8) ?? "")
        }

        let decoded = try JSONDecoder().decode(ChatCompletionResponse.self, from: data)
        guard let content = decoded.choices.first?.message.content, !content.isEmpty else {
            throw ProxyAPIError.empty
        }
        return content
    }
}
