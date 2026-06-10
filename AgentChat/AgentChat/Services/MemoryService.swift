import Foundation

/// Мета-операции над памятью: сжатие диалога, извлечение фактов, экспорт.
/// Все LLM-вызовы — на самой дешёвой модели (cost-sensitive).
struct MemoryService {
    private let client: ProxyAPIClient
    private let cheapModel = "gemini/gemini-2.5-flash-lite"

    init(client: ProxyAPIClient = ProxyAPIClient()) {
        self.client = client
    }

    /// Сжать старую часть диалога в summary (дописать к предыдущей выжимке).
    func summarize(previous: String?, overflow: [ChatMessage]) async throws -> String {
        let system = """
        Ты сжимаешь диалог в краткую выжимку для памяти ассистента. Сохрани важное: \
        имена, факты, предпочтения, договорённости, нерешённые вопросы. Без воды, \
        по-русски, до 120 слов. Верни только саму выжимку, без пояснений.
        """
        var body = ""
        if let previous, !previous.isEmpty {
            body += "Уже известная выжимка:\n\(previous)\n\n"
        }
        body += "Новая часть диалога:\n" + transcript(overflow)

        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: body, imageDataURL: nil)
        ]
        return try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.3, maxTokens: 400)
        )
    }

    /// Обновить факты о пользователе по новому диалогу: добавить новое, ЗАМЕНИТЬ
    /// изменившееся (возраст, город, статус), объединить дубли, убрать противоречия.
    /// Возвращает ПОЛНЫЙ обновлённый список (не только новое).
    func updatedFacts(known: [String], messages: [ChatMessage]) async throws -> [String] {
        let system = """
        Тебе дан список текущих фактов о пользователе и новый диалог. Верни ОБНОВЛЁННЫЙ \
        полный список фактов:
        - добавь новые факты из диалога;
        - ЗАМЕНИ изменившиеся (например возраст, город, статус — новое значение вместо старого);
        - объедини дубли и близкое по смыслу;
        - убери устаревшее и противоречивое.
        По одному факту на строку, без нумерации, кратко. Только реальные факты, не выдумывай. \
        Сохрани все актуальные факты, не теряй важное. До ~20 фактов.
        """
        let body = "Текущие факты:\n"
            + (known.isEmpty ? "—" : known.joined(separator: "\n"))
            + "\n\nНовый диалог:\n" + transcript(messages)

        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: body, imageDataURL: nil)
        ]
        let raw = try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.2, maxTokens: 500)
        )
        let updated = parseFacts(raw, known: [])
        return updated.isEmpty ? known : updated   // safety: не теряем память
    }

    /// Почистить список фактов: объединить дубли/близкое, убрать устаревшее и
    /// противоречивое. Агент сам приводит память в порядок (дешёвая модель).
    func consolidate(facts: [String]) async throws -> [String] {
        guard facts.count > 1 else { return facts }
        let system = """
        Ты чистишь список фактов о пользователе. Объедини дубли и близкое по смыслу, \
        убери устаревшие и противоречивые, оставь только актуальные и важные. По одному \
        факту на строку, кратко, без нумерации. Не выдумывай новых фактов.
        """
        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: facts.joined(separator: "\n"), imageDataURL: nil)
        ]
        let raw = try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.2, maxTokens: 400)
        )
        let cleaned = parseFacts(raw, known: [])
        return cleaned.isEmpty ? facts : cleaned   // safety: не обнуляем память
    }

    /// JSON-снимок: что реально уходит в модель (system + окно) + хранимое
    /// (факты, summary, вся история). Для наглядности (видео/гит).
    func exportJSON(
        agentName: String,
        model: String,
        system: String,
        window: [ChatMessage],
        facts: [String],
        summary: String?,
        fullHistory: [ChatMessage]
    ) -> String {
        struct ExportMessage: Encodable {
            let role: String
            let content: String
            let createdAt: String
        }
        struct Export: Encodable {
            // что УХОДИТ в модель перед ответом:
            let agent: String
            let model: String
            let systemPrompt: String
            let contextWindow: [ExportMessage]
            // что ХРАНИТСЯ:
            let facts: [String]
            let summary: String?
            let fullHistory: [ExportMessage]
        }

        let iso = ISO8601DateFormatter()
        let map: ([ChatMessage]) -> [ExportMessage] = { msgs in
            msgs.map { ExportMessage(role: $0.role.rawValue, content: $0.content, createdAt: iso.string(from: $0.createdAt)) }
        }
        let export = Export(
            agent: agentName,
            model: model,
            systemPrompt: system,
            contextWindow: map(window),
            facts: facts,
            summary: summary,
            fullHistory: map(fullHistory)
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes, .sortedKeys]
        guard let data = try? encoder.encode(export), let json = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return json
    }

    // MARK: - Helpers

    private func transcript(_ messages: [ChatMessage]) -> String {
        messages.map { msg in
            let who = msg.role == .user ? "Пользователь" : (msg.role == .assistant ? "Ассистент" : "Система")
            return "\(who): \(msg.content)"
        }.joined(separator: "\n")
    }

    private func parseFacts(_ raw: String, known: [String]) -> [String] {
        let knownLower = Set(known.map { $0.lowercased() })
        var seen = Set<String>()
        var result: [String] = []
        for line in raw.components(separatedBy: "\n") {
            var fact = line.trimmingCharacters(in: .whitespaces)
            while let first = fact.first, "-*•0123456789. ".contains(first) {
                fact.removeFirst()
                fact = fact.trimmingCharacters(in: .whitespaces)
            }
            guard fact.count >= 3 else { continue }
            let lower = fact.lowercased()
            // отсеять no-op ответы модели («нет новых фактов» и т.п.)
            if lower.hasPrefix("нет ") || lower.contains("новых фактов") || lower == "—" || lower == "-" {
                continue
            }
            guard !knownLower.contains(lower), !seen.contains(lower) else { continue }
            seen.insert(lower)
            result.append(fact)
        }
        return result
    }
}
