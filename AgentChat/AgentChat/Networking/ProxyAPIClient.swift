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
    var stream: Bool = false

    enum CodingKeys: String, CodingKey { case model, messages, temperature, max_tokens, stream, stream_options }
    private struct StreamOptions: Encodable { let include_usage: Bool }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(model, forKey: .model)
        try c.encode(messages, forKey: .messages)
        try c.encode(max_tokens, forKey: .max_tokens)
        if let temperature { try c.encode(temperature, forKey: .temperature) }
        if stream {
            try c.encode(true, forKey: .stream)
            try c.encode(StreamOptions(include_usage: true), forKey: .stream_options)
        }
    }
}

private struct ChatCompletionResponse: Decodable {
    struct Choice: Decodable {
        struct Message: Decodable { let content: String }
        let message: Message
    }
    let choices: [Choice]
}

/// Один SSE-чанк стриминга: либо кусок текста (delta), либо финальный usage.
private struct StreamChunk: Decodable {
    struct Choice: Decodable {
        struct Delta: Decodable { let content: String? }
        let delta: Delta?
    }
    let choices: [Choice]?
    let usage: TokenUsage?
}

/// Событие стрима: дельта текста или итоговый usage (приходит финальным чанком).
enum StreamEvent {
    case delta(String)
    case usage(TokenUsage)
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

    /// Стриминг ответа (SSE). Отдаёт дельты текста по мере генерации и финальный usage.
    /// Ошибки (вкл. 400 при переполнении контекста) бросаются как ProxyAPIError.http.
    func completeStreaming(messages: [ChatMessageRequest], model: String, params: GenerationParams) -> AsyncThrowingStream<StreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let work = Task {
                do {
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
                            max_tokens: params.maxTokens,
                            stream: true
                        )
                    )

                    let (bytes, response) = try await URLSession.shared.bytes(for: request)
                    guard let http = response as? HTTPURLResponse else { throw ProxyAPIError.invalidResponse }
                    guard (200..<300).contains(http.statusCode) else {
                        var body = ""
                        for try await line in bytes.lines { body += line }
                        throw ProxyAPIError.http(status: http.statusCode, body: body)
                    }

                    for try await line in bytes.lines {
                        guard line.hasPrefix("data:") else { continue }
                        let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                        if payload == "[DONE]" { break }
                        guard let data = payload.data(using: .utf8),
                              let chunk = try? JSONDecoder().decode(StreamChunk.self, from: data) else { continue }
                        if let content = chunk.choices?.first?.delta?.content, !content.isEmpty {
                            continuation.yield(.delta(content))
                        }
                        if let usage = chunk.usage {
                            continuation.yield(.usage(usage))
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in work.cancel() }
        }
    }
}
