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

    init(name: String, emoji: String, systemPrompt: String, isBuiltIn: Bool = false) {
        self.id = UUID()
        self.name = name
        self.emoji = emoji
        self.systemPrompt = systemPrompt
        self.isBuiltIn = isBuiltIn
        self.createdAt = Date()
        self.facts = []
    }
}

extension AgentProfile {
    private struct Preset {
        let name: String
        let emoji: String
        let prompt: String
    }

    /// Встроенные агенты, которые надо удалить у тех, у кого они уже засеяны.
    private static let deprecatedBuiltIns: Set<String> = ["Аладдин", "Шут"]

    private static let builtInPresets: [Preset] = [
        Preset(
            name: "Акс",
            emoji: "🧠",
            prompt: """
            Тебя зовут Акс. Ты — очень умный эрудит-помощник, разбираешься в любом вопросе \
            и подскажешь по делу. Отвечай точно, структурированно и по существу: факты, шаги, \
            примеры. Сложный вопрос — разложи на пункты. Не выдумывай: если не уверен — прямо \
            скажи и предложи, как проверить.
            """
        )
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
                isBuiltIn: true
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
