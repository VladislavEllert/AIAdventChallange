import Foundation

struct ChatMessage: Identifiable, Hashable {
    let id: UUID
    let role: Role
    var content: String          // var: стриминг дописывает ответ по дельтам
    let imageData: Data?
    let createdAt: Date
    var usage: TokenUsage?        // точный расход токенов (для ответа модели)
    var responseTime: TimeInterval?  // время ответа, сек (от отправки до конца стрима)
    var modelID: String?          // какая модель сгенерировала ответ (для расчёта ₽)

    init(role: Role, content: String, imageData: Data? = nil, usage: TokenUsage? = nil, responseTime: TimeInterval? = nil, modelID: String? = nil) {
        self.id = UUID()
        self.role = role
        self.content = content
        self.imageData = imageData
        self.createdAt = Date()
        self.usage = usage
        self.responseTime = responseTime
        self.modelID = modelID
    }
}
