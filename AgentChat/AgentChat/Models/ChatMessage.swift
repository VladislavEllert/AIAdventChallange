import Foundation

struct ChatMessage: Identifiable, Hashable {
    let id: UUID
    let role: Role
    let content: String
    let imageData: Data?
    let createdAt: Date

    init(role: Role, content: String, imageData: Data? = nil) {
        self.id = UUID()
        self.role = role
        self.content = content
        self.imageData = imageData
        self.createdAt = Date()
    }
}
