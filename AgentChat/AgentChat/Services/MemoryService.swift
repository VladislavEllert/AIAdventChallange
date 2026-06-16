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
    /// maxWords — бюджет длины выжимки (жёстче компрессия → короче).
    func summarize(previous: String?, overflow: [ChatMessage], maxWords: Int = 120) async throws -> String {
        let system = """
        Ты сжимаешь диалог в краткую выжимку для памяти ассистента. Сохрани важное: \
        имена, факты, предпочтения, договорённости, нерешённые вопросы. Без воды, \
        по-русски, до \(maxWords) слов. Верни только саму выжимку, без пояснений.
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

        Записывай ТОЛЬКО долговременные факты О САМОМ ПОЛЬЗОВАТЕЛЕ: имя, возраст/др, учёба/работа, \
        город, близкие и питомцы, вещи, устойчивые предпочтения, постоянные цели/проекты.
        НЕ записывай (это НЕ факты о пользователе):
        - детали текущего разговора/чата («первое сообщение было…», «спросил про…», «обсуждали…»);
        - текущую дату/время и сиюминутные состояния (быстро устаревают);
        - факты о мире и новостях (последний iPhone, курсы, события) — это не про пользователя;
        - инструкции, имя или персону самого ассистента.

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

    /// Sticky Facts (день-10): обновить KV-память по диалогу. Категории-ключи —
    /// Цель / Ограничения / Предпочтения / Решения / Договорённости (+ уточнённые).
    /// Возвращает ПОЛНЫЙ обновлённый список пар «ключ-значение».
    func stickyFacts(current: [FactKV], conversation: [ChatMessage]) async throws -> [FactKV] {
        let system = """
        Ты ведёшь компактную KV-память по диалогу сбора ТЗ. Ключи — категории важного: \
        Цель, Ограничения, Предпочтения, Решения, Договорённости (можно уточнённые ключи: \
        «Бюджет», «Сроки», «Стек», «Аудитория» и т.п.). На входе — текущие факты и диалог. \
        Верни ОБНОВЛЁННЫЙ полный список строк формата «ключ: значение»: добавь новое, \
        ЗАМЕНИ изменившееся, убери противоречия и дубли. Только важное из диалога, не выдумывай. \
        Кратко, по-русски, без пояснений и нумерации, по одной паре на строку. До ~12 строк.
        """
        let body = "Текущие факты:\n"
            + (current.isEmpty ? "—" : current.map { "\($0.key): \($0.value)" }.joined(separator: "\n"))
            + "\n\nДиалог:\n" + transcript(conversation)

        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: body, imageDataURL: nil)
        ]
        let raw = try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.2, maxTokens: 400)
        )
        let parsed = parseKV(raw)
        return parsed.isEmpty ? current : parsed   // safety: не теряем память
    }

    /// Долговременная память (день-11): обновить глобальный профиль пользователя по диалогу.
    /// Строгий фильтр: ТОЛЬКО личная инфа о юзере. Без дубликатов (сравнивает с current).
    func updateGlobalProfile(current: String, messages: [ChatMessage]) async throws -> String {
        let system = """
        Ты обновляешь долговременный профиль пользователя. \
        Добавляй ТОЛЬКО личные факты: имя, возраст, город, образование/работа, \
        интересы, стиль общения, долгосрочные цели/проекты, важные предпочтения.

        НЕ добавляй (это НЕ долговременная память):
        - детали текущей задачи, технические решения конкретного кода — это рабочая память;
        - сиюминутные состояния, текущую дату/время;
        - то что уже есть в «Текущий профиль» (не дублируй, даже близким по смыслу).
        - новости, факты о мире.

        Верни ОБНОВЛЁННЫЙ профиль: текущее оставь как есть, добавь только НОВЫЕ строки \
        из диалога. Формат: «- факт» на каждой строке, по-русски, кратко. \
        Если новых фактов нет — верни текущий профиль без изменений, без добавлений.
        Максимум 20 строк итого.
        """
        let body = "Текущий профиль:\n\(current.isEmpty ? "—" : current)\n\nДиалог:\n" + transcript(messages)
        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: body, imageDataURL: nil)
        ]
        return try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.2, maxTokens: 400)
        )
    }

    /// Рабочая память (день-11): извлечь контекст текущей задачи из диалога.
    /// Объединяет с existing (если есть), убирает дубли. Дешёвая модель.
    func extractTaskContext(messages: [ChatMessage], existing: String?) async throws -> String {
        let system = """
        Из диалога извлеки: текущую задачу, принятые решения, важный технический контекст. \
        Кратко, bullet-points, по-русски. Если есть «Уже сохранено» — объедини с ним, убери дубли. \
        Только то, что реально обсуждалось. До 8 пунктов. Верни только список, без пояснений.
        """
        var body = ""
        if let existing, !existing.isEmpty {
            body += "Уже сохранено:\n\(existing)\n\n"
        }
        body += "Диалог:\n" + transcript(messages)

        let requests = [
            ChatMessageRequest(role: .system, text: system, imageDataURL: nil),
            ChatMessageRequest(role: .user, text: body, imageDataURL: nil)
        ]
        return try await client.complete(
            messages: requests,
            model: cheapModel,
            params: GenerationParams(temperature: 0.2, maxTokens: 300)
        )
    }

    /// Почистить список фактов: объединить дубли/близкое, убрать устаревшее и
    /// противоречивое. Агент сам приводит память в порядок (дешёвая модель).
    func consolidate(facts: [String]) async throws -> [String] {
        guard facts.count > 1 else { return facts }
        let system = """
        Ты чистишь список фактов о пользователе. Объедини дубли и близкое по смыслу, \
        убери устаревшие и противоречивые, оставь только актуальные и важные.

        Удали записи, которые НЕ являются долговременными фактами о пользователе:
        - детали конкретного чата («первое сообщение было…», «спросил про…»);
        - текущую дату/время и сиюминутные состояния;
        - факты о мире и новостях (последний iPhone, курсы, события);
        - инструкции, имя или персону самого ассистента.

        По одному факту на строку, кратко, без нумерации. Не выдумывай новых фактов.
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
            let promptTokens: Int?
            let completionTokens: Int?
            let reasoningTokens: Int?
            let totalTokens: Int?
            let costRub: Double?
            let responseTimeSec: Double?
        }
        struct TokensSummary: Encodable {
            let promptTokens: Int
            let completionTokens: Int
            let reasoningTokens: Int
            let totalTokens: Int
            let costRub: Double
            let answers: Int
        }
        // Порядок полей = порядок объявления (sortedKeys выключен): сверху главное
        // (расход токенов, summary, факты), тяжёлое (массивы, большой systemPrompt) — внизу.
        struct Export: Encodable {
            let agent: String
            let model: String
            let tokens: TokensSummary          // расход токенов по чату
            let summary: String?               // сжатая выжимка старого
            let facts: [String]                // долгая память (не трогается сжатием)
            let contextWindow: [ExportMessage] // что УХОДИТ в модель сейчас (после сжатия — коротко)
            let fullHistory: [ExportMessage]   // весь архив переписки
            let systemPrompt: String           // весь собранный system (персона+факты+summary)
        }

        let iso = ISO8601DateFormatter()
        let map: ([ChatMessage]) -> [ExportMessage] = { msgs in
            msgs.map { m in
                let u = m.usage
                let cost = u.map { LLMModel.by(id: m.modelID).cost($0) }
                return ExportMessage(
                    role: m.role.rawValue,
                    content: m.content,
                    createdAt: iso.string(from: m.createdAt),
                    promptTokens: u?.promptTokens,
                    completionTokens: u?.completionTokens,
                    reasoningTokens: u?.reasoningTokens,
                    totalTokens: u?.totalTokens,
                    costRub: cost,
                    responseTimeSec: m.responseTime
                )
            }
        }
        let tokens = TokensSummary(
            promptTokens: fullHistory.compactMap { $0.usage?.promptTokens }.reduce(0, +),
            completionTokens: fullHistory.compactMap { $0.usage?.completionTokens }.reduce(0, +),
            reasoningTokens: fullHistory.compactMap { $0.usage?.reasoningTokens }.reduce(0, +),
            totalTokens: fullHistory.compactMap { $0.usage?.totalTokens }.reduce(0, +),
            costRub: fullHistory.reduce(0) { acc, m in
                guard let u = m.usage else { return acc }
                return acc + LLMModel.by(id: m.modelID).cost(u)
            },
            answers: fullHistory.filter { $0.usage != nil }.count
        )
        let export = Export(
            agent: agentName,
            model: model,
            tokens: tokens,
            summary: summary,
            facts: facts,
            contextWindow: map(window),
            fullHistory: map(fullHistory),
            systemPrompt: system
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
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

    /// Распарсить ответ модели в KV-пары «ключ: значение» (по строкам).
    private func parseKV(_ raw: String) -> [FactKV] {
        var seen = Set<String>()
        var result: [FactKV] = []
        for line in raw.components(separatedBy: "\n") {
            var s = line.trimmingCharacters(in: .whitespaces)
            while let first = s.first, "-*•0123456789. ".contains(first) {
                s.removeFirst()
                s = s.trimmingCharacters(in: .whitespaces)
            }
            guard let sep = s.firstIndex(of: ":") else { continue }
            let key = String(s[..<sep]).trimmingCharacters(in: .whitespaces)
            let value = String(s[s.index(after: sep)...]).trimmingCharacters(in: .whitespaces)
            guard key.count >= 2, value.count >= 1 else { continue }
            let lowerKey = key.lowercased()
            guard !seen.contains(lowerKey) else { continue }
            seen.insert(lowerKey)
            result.append(FactKV(key: key, value: value))
        }
        return result
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
