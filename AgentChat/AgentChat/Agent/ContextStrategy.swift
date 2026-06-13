import Foundation

/// Стратегия управления контекстом агента.
/// `.standard` — «мои» агенты (summary-стек дня 7/9). Остальные три — курсовые
/// тест-агенты дня-10 (без summary).
enum ContextStrategyKind: String, Codable, CaseIterable {
    case standard
    case slidingWindow
    case stickyFacts
    case branching

    var displayName: String {
        switch self {
        case .standard: return "Стандарт (summary)"
        case .slidingWindow: return "Скользящее окно"
        case .stickyFacts: return "Факты KV"
        case .branching: return "Ветки"
        }
    }

    /// Короткое описание для UI-индикатора.
    var shortHint: String {
        switch self {
        case .standard: return "summary + долгие факты"
        case .slidingWindow: return "только последние N сообщений"
        case .stickyFacts: return "KV-факты + последние N"
        case .branching: return "ветки диалога, без сжатия"
        }
    }

    /// Окно по умолчанию для стратегий, у которых оно есть.
    var defaultWindow: Int { 8 }

    /// Честное самознание агента о СВОЁМ механизме памяти — кладём в system-промпт,
    /// чтобы агент правильно отвечал на «как ты управляешь памятью».
    func memorySelfKnowledge(window: Int) -> String {
        switch self {
        case .standard:
            return ""
        case .slidingWindow:
            return """
            Как устроена твоя память (отвечай честно, если спросят): стратегия «Скользящее окно». \
            Тебе передаются только последние \(window) сообщений диалога. Всё, что старше окна, \
            тебе НЕ показывают — ты этого не помнишь и не должен делать вид, что помнишь. \
            Summary и долгих фактов у тебя нет.
            """
        case .stickyFacts:
            return """
            Как устроена твоя память (отвечай честно, если спросят): стратегия «Sticky Facts (KV)». \
            После каждого сообщения пользователя из диалога извлекается блок ключевых фактов \
            (ключ-значение: цель, ограничения, предпочтения, решения, договорённости). \
            В каждый запрос тебе дают этот KV-блок + последние \(window) сообщений. Старые сообщения \
            вне окна ты помнишь только через факты в KV-блоке. Summary у тебя нет.
            """
        case .branching:
            return """
            Как устроена твоя память (отвечай честно, если спросят): стратегия «Ветки диалога». \
            Диалог может ветвиться от любой точки. Ты видишь ЦЕЛИКОМ только активную ветку \
            (без сжатия). Сообщения из других веток тебе не передаются — ты их не знаешь. \
            Summary и долгих фактов у тебя нет.
            """
        }
    }

    /// Рантайм-стратегия. `.standard` → nil (старый путь Agent без делегирования).
    func make() -> ContextStrategy? {
        switch self {
        case .standard: return nil
        case .slidingWindow: return SlidingWindowStrategy(n: defaultWindow)
        case .stickyFacts: return StickyFactsStrategy(n: defaultWindow)
        case .branching: return BranchingStrategy()
        }
    }
}

/// Пара ключ-значение для Sticky Facts (цель / ограничение / предпочтение / решение / договорённость).
struct FactKV: Codable, Identifiable, Equatable {
    var key: String
    var value: String
    var id: String { key }
}

/// Вход для сборки запроса стратегией.
struct StrategyInput {
    let history: [ChatMessage]
    let facts: [FactKV]
}

/// Стратегия отвечает на один вопрос: ЧТО уходит в модель на этом ходу —
/// какое окно сообщений и какой доп-блок в system. Без сайд-эффектов
/// (извлечение KV-фактов и ветвление оркеструет ViewModel).
protocol ContextStrategy {
    var kind: ContextStrategyKind { get }
    /// Сообщения, реально уходящие в модель (без system и текущего ввода).
    func window(_ history: [ChatMessage]) -> [ChatMessage]
    /// Доп-текст к system-промпту (например KV-блок фактов).
    func systemAddition(_ input: StrategyInput) -> String
}

extension ContextStrategy {
    func systemAddition(_ input: StrategyInput) -> String { "" }
}

/// Стратегия 1: храним/шлём только последние N сообщений, остальное отбрасываем.
struct SlidingWindowStrategy: ContextStrategy {
    let n: Int
    var kind: ContextStrategyKind { .slidingWindow }
    func window(_ history: [ChatMessage]) -> [ChatMessage] { Array(history.suffix(n)) }
}

/// Стратегия 2: отдельный KV-блок важных фактов + последние N сообщений.
/// Факты обновляются ViewModel'ом после каждого сообщения юзера.
struct StickyFactsStrategy: ContextStrategy {
    let n: Int
    var kind: ContextStrategyKind { .stickyFacts }
    func window(_ history: [ChatMessage]) -> [ChatMessage] { Array(history.suffix(n)) }
    func systemAddition(_ input: StrategyInput) -> String {
        guard !input.facts.isEmpty else { return "" }
        let lines = input.facts.map { "- \($0.key): \($0.value)" }.joined(separator: "\n")
        return """
        Твоя внутренняя память по диалогу (служебный контекст, НЕ для показа). \
        НЕ выводи её пользователю, НЕ повторяй списком и не пересказывай в ответе — \
        просто учитывай при разговоре:
        \(lines)
        """
    }
}

/// Стратегия 3: ветки диалога. Активная ветка — уже линейная нить, шлём её
/// целиком без обрезки/summary. Ветвление и переключение делает ViewModel.
struct BranchingStrategy: ContextStrategy {
    var kind: ContextStrategyKind { .branching }
    func window(_ history: [ChatMessage]) -> [ChatMessage] { history }
}
