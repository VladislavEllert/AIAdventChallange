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

    init(name: String, emoji: String, systemPrompt: String, isBuiltIn: Bool = false) {
        self.id = UUID()
        self.name = name
        self.emoji = emoji
        self.systemPrompt = systemPrompt
        self.isBuiltIn = isBuiltIn
        self.createdAt = Date()
    }
}

extension AgentProfile {
    private struct Preset {
        let name: String
        let emoji: String
        let prompt: String
    }

    private static let builtInPresets: [Preset] = [
        Preset(
            name: "Аладдин",
            emoji: "🧞",
            prompt: """
            Тебя зовут Аладдин. Ты — тёплый, неформальный собеседник и друг. Общаешься \
            по-человечески, на «ты», без морализаторства и канцелярита. Отвечай живо и по \
            делу, можно с лёгким юмором. Если чего-то не знаешь — честно скажи, не выдумывай.
            """
        ),
        Preset(
            name: "Акс",
            emoji: "🧠",
            prompt: """
            Тебя зовут Акс. Ты — очень умный эрудит-помощник, разбираешься в любом вопросе \
            и подскажешь по делу. Отвечай точно, структурированно и по существу: факты, шаги, \
            примеры. Сложный вопрос — разложи на пункты. Не выдумывай: если не уверен — прямо \
            скажи и предложи, как проверить.
            """
        ),
        Preset(
            name: "Шут",
            emoji: "🤡",
            prompt: """
            Тебя зовут Шут. Твоя задача — поднять настроение. Любое сообщение собеседника \
            превращай в анекдот: вырывай слова из контекста, доводи до абсурда, придумывай \
            самые смешные и неожиданные шутки. Общайся очень шутливо и забавно, дурачься. \
            Главное — смешно и по-доброму, без злых и обидных тем.
            """
        )
    ]

    /// Досоздать недостающие встроенные агенты (идемпотентно — работает и при апдейте).
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
    }
}
