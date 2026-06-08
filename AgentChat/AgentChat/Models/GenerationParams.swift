import Foundation

struct GenerationParams: Codable {
    var temperature: Double
    var maxTokens: Int

    static let bro = GenerationParams(temperature: 0.8, maxTokens: 512)
}
