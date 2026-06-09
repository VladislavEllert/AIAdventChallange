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
}

@Model
final class StoredMessage {
    var id: UUID
    var roleRaw: String
    var content: String
    var imageData: Data?
    var createdAt: Date
    var chat: ChatSession?

    init(role: Role, content: String, imageData: Data? = nil) {
        self.id = UUID()
        self.roleRaw = role.rawValue
        self.content = content
        self.imageData = imageData
        self.createdAt = Date()
    }

    var role: Role { Role(rawValue: roleRaw) ?? .user }

    var asChatMessage: ChatMessage {
        ChatMessage(role: role, content: content, imageData: imageData)
    }
}
