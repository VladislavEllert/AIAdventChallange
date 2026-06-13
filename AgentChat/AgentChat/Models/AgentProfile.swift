import Foundation
import SwiftData

/// Персистентный агент: личность (имя, эмодзи, системный промпт). Пресеты нельзя
/// удалить (isBuiltIn). Пользователь создаёт своих.
@Model
final class AgentProfile {
    var id: UUID
    var name: String
    var emoji: String
    var systemPrompt: String
    var isBuiltIn: Bool
    var createdAt: Date
    /// Долгая память: стойкие факты о пользователе. Живут между чатами этого агента.
    var facts: [String] = []
    /// Стратегия управления контекстом. «Мои» агенты — standard; курсовые тест-агенты — три стратегии дня-10.
    var strategyRaw: String = ContextStrategyKind.standard.rawValue
    /// Курсовой тест-агент (вкладка «Тестовые»). Отделяет полигон от «моих» агентов.
    var isCourseTest: Bool = false

    init(name: String, emoji: String, systemPrompt: String, isBuiltIn: Bool = false,
         strategy: ContextStrategyKind = .standard, isCourseTest: Bool = false) {
        self.id = UUID()
        self.name = name
        self.emoji = emoji
        self.systemPrompt = systemPrompt
        self.isBuiltIn = isBuiltIn
        self.createdAt = Date()
        self.facts = []
        self.strategyRaw = strategy.rawValue
        self.isCourseTest = isCourseTest
    }

    var strategy: ContextStrategyKind {
        ContextStrategyKind(rawValue: strategyRaw) ?? .standard
    }
}

extension AgentProfile {
    private struct Preset {
        let name: String
        let emoji: String
        let prompt: String
        var strategy: ContextStrategyKind = .standard
        var isCourseTest: Bool = false
    }

    /// Встроенные агенты, которые надо удалить у тех, у кого они уже засеяны.
    private static let deprecatedBuiltIns: Set<String> = ["Аладдин", "Шут", "Акс"]

    /// Общий промпт для тест-агентов: один и тот же сценарий, разная только память.
    private static let testPrompt = """
    Ты — ассистент-аналитик, помогаешь собрать ТЗ на проект. Веди диалог по делу: \
    уточняй цель, ограничения, предпочтения, фиксируй договорённости и решения. \
    Отвечай кратко и конкретно. Не выдумывай — если детали не хватает, спроси.
    """

    private static let builtInPresets: [Preset] = [
        // Курсовые тест-агенты дня-10 — три стратегии управления контекстом (без summary).
        Preset(name: "Окно N", emoji: "🪟", prompt: testPrompt,
               strategy: .slidingWindow, isCourseTest: true),
        Preset(name: "Факты KV", emoji: "🗂️", prompt: testPrompt,
               strategy: .stickyFacts, isCourseTest: true),
        Preset(name: "Ветки", emoji: "🌿", prompt: testPrompt,
               strategy: .branching, isCourseTest: true)
    ]

    /// Досоздать недостающие встроенные агенты (идемпотентно) + убрать устаревшие.
    static func ensureBuiltIns(_ context: ModelContext) {
        let existing = (try? context.fetch(
            FetchDescriptor<AgentProfile>(predicate: #Predicate { $0.isBuiltIn })
        )) ?? []
        let names = Set(existing.map { $0.name })

        for preset in builtInPresets where !names.contains(preset.name) {
            context.insert(AgentProfile(
                name: preset.name,
                emoji: preset.emoji,
                systemPrompt: preset.prompt,
                isBuiltIn: true,
                strategy: preset.strategy,
                isCourseTest: preset.isCourseTest
            ))
        }

        // Удалить устаревшие встроенные агенты по точному имени (+ их чаты).
        for agent in existing where deprecatedBuiltIns.contains(agent.name) {
            let agentID: UUID? = agent.id
            if let chats = try? context.fetch(
                FetchDescriptor<ChatSession>(predicate: #Predicate { $0.agentID == agentID })
            ) {
                chats.forEach { context.delete($0) }
            }
            context.delete(agent)
        }

        // Осиротевшие встроенные (переименованные/кастомные, не из пресетов и не в deprecated)
        // → перевести в «Свой»: их можно удалять, они не висят как «Встроенный».
        let presetNames = Set(builtInPresets.map { $0.name })
        for agent in existing
        where !deprecatedBuiltIns.contains(agent.name) && !presetNames.contains(agent.name) {
            agent.isBuiltIn = false
        }
    }
}
