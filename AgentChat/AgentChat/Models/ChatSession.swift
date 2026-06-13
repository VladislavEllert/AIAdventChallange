import Foundation
import SwiftData

/// Чат — персистентная сущность (переживает перезапуск). Хранит сообщения.
@Model
final class ChatSession {
    var id: UUID
    var title: String
    var createdAt: Date
    var agentID: UUID?
    /// Сжатая выжимка старой части диалога (компрессия контекста).
    var summary: String?
    /// Sticky Facts (день-10): KV-факты этого чата, сериализованы в JSON. Обновляются после каждого сообщения юзера.
    var stickyFactsData: Data?
    /// Branching (день-10): активная ветка диалога. nil → ветвление не используется (обычный линейный чат).
    var activeBranchID: UUID?
    @Relationship(deleteRule: .cascade, inverse: \StoredMessage.chat)
    var messages: [StoredMessage]

    init(agentID: UUID, title: String = "Новый чат") {
        self.id = UUID()
        self.title = title
        self.createdAt = Date()
        self.agentID = agentID
        self.summary = nil
        self.messages = []
    }

    var sortedMessages: [StoredMessage] {
        messages.sorted { $0.createdAt < $1.createdAt }
    }

    /// KV-факты Sticky Facts (декодируются из stickyFactsData).
    var stickyFacts: [FactKV] {
        get { stickyFactsData.flatMap { try? JSONDecoder().decode([FactKV].self, from: $0) } ?? [] }
        set { stickyFactsData = try? JSONEncoder().encode(newValue) }
    }
}

/// Ветка диалога (день-10, стратегия Branching). Каждая ветка — независимая линейная нить
/// сообщений (StoredMessage с этим branchID). Форк копирует префикс родителя в новую ветку.
@Model
final class ConversationBranch {
    var id: UUID
    var chatID: UUID?
    var name: String
    var parentBranchID: UUID?
    var createdAt: Date
    /// Основная (каноническая) ветка чата. Дефолт при открытии + цель отката при удалении.
    var isMain: Bool = false

    init(chatID: UUID, name: String, parentBranchID: UUID? = nil, isMain: Bool = false) {
        self.id = UUID()
        self.chatID = chatID
        self.name = name
        self.parentBranchID = parentBranchID
        self.createdAt = Date()
        self.isMain = isMain
    }
}

@Model
final class StoredMessage {
    var id: UUID
    var roleRaw: String
    var content: String
    var imageData: Data?
    var createdAt: Date
    var chat: ChatSession?
    // Расход токенов и время ответа (для ответа модели). Переживают перезапуск.
    var promptTokens: Int?
    var completionTokens: Int?
    var reasoningTokens: Int?
    var responseTime: Double?
    var modelID: String?
    /// Branching (день-10): к какой ветке относится сообщение. nil → обычный линейный чат.
    var branchID: UUID?

    init(role: Role, content: String, imageData: Data? = nil, usage: TokenUsage? = nil, responseTime: Double? = nil, modelID: String? = nil, branchID: UUID? = nil) {
        self.id = UUID()
        self.roleRaw = role.rawValue
        self.content = content
        self.imageData = imageData
        self.createdAt = Date()
        self.branchID = branchID
        self.promptTokens = usage?.promptTokens
        self.completionTokens = usage?.completionTokens
        self.reasoningTokens = usage?.reasoningTokens
        self.responseTime = responseTime
        self.modelID = modelID
    }

    var role: Role { Role(rawValue: roleRaw) ?? .user }

    var usage: TokenUsage? {
        guard let promptTokens, let completionTokens else { return nil }
        return TokenUsage(
            promptTokens: promptTokens,
            completionTokens: completionTokens,
            totalTokens: promptTokens + completionTokens,
            reasoningTokens: reasoningTokens
        )
    }

    var asChatMessage: ChatMessage {
        ChatMessage(role: role, content: content, imageData: imageData, usage: usage, responseTime: responseTime, modelID: modelID)
    }
}
