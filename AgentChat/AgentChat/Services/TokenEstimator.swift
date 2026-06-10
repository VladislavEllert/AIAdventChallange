import Foundation

/// Грубая локальная оценка числа токенов ДО отправки (точное число даёт только API).
/// Метод: символов / k. Коэффициент k («символов на токен») самокалибруется по реальному
/// usage из последнего ответа — у разных провайдеров/языков токенайзеры разные.
enum TokenEstimator {
    /// Стартовый коэффициент (смешанный RU/EN; кириллица плотнее ~ латиницы).
    static let defaultCharsPerToken = 3.5

    static func estimate(_ text: String, charsPerToken k: Double = defaultCharsPerToken) -> Int {
        guard !text.isEmpty else { return 0 }
        let k = k > 0 ? k : defaultCharsPerToken
        return max(1, Int(ceil(Double(text.count) / k)))
    }

    /// Откалибровать k по факту: сколько символов реально ушло в модель против prompt_tokens.
    static func calibrate(sentChars: Int, promptTokens: Int) -> Double? {
        guard sentChars > 0, promptTokens > 0 else { return nil }
        return Double(sentChars) / Double(promptTokens)
    }
}
