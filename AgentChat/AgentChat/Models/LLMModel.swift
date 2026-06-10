import Foundation

/// Каталог моделей ProxyAPI. id, цены (₽ за 1М токенов) сверены живым запросом
/// `/v1/models` + пробным вызовом и прайсом proxyapi.ru/pricing/list (2026-06).
struct LLMModel: Identifiable, Hashable {
    let id: String        // id для ProxyAPI (роутинг по имени)
    let name: String      // отображаемое имя
    let provider: String  // Google / OpenAI / Anthropic
    let inPrice: Int       // ₽ за 1М входных токенов
    let outPrice: Int      // ₽ за 1М выходных токенов
    let contextLimit: Int  // лимит контекстного окна (токенов) — сверено с доками провайдеров
    var web: Bool = false                  // встроенный веб-поиск (живой интернет)
    var supportsTemperature: Bool = true   // search-модели не принимают temperature

    var priceShort: String { "\(inPrice)/\(outPrice) ₽" }
    var priceFull: String { "ввод \(inPrice) ₽ · вывод \(outPrice) ₽ за 1М токенов" }

    /// Стоимость одного обмена в рублях по точному usage.
    func cost(_ usage: TokenUsage) -> Double {
        Double(usage.promptTokens) / 1_000_000 * Double(inPrice)
        + Double(usage.completionTokens) / 1_000_000 * Double(outPrice)
    }

    static let all: [LLMModel] = [
        LLMModel(id: "gemini/gemini-2.5-flash-lite", name: "Gemini 2.5 Flash Lite", provider: "Google", inPrice: 26, outPrice: 129, contextLimit: 1_048_576),
        LLMModel(id: "gemini/gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "Google", inPrice: 78, outPrice: 645, contextLimit: 1_048_576),
        LLMModel(id: "openai/gpt-4o-mini", name: "GPT-4o mini", provider: "OpenAI", inPrice: 39, outPrice: 155, contextLimit: 128_000),
        LLMModel(id: "openai/gpt-4o", name: "GPT-4o", provider: "OpenAI", inPrice: 645, outPrice: 2577, contextLimit: 128_000),
        LLMModel(id: "anthropic/claude-haiku-4-5", name: "Claude Haiku 4.5", provider: "Anthropic", inPrice: 295, outPrice: 1474, contextLimit: 200_000),
        LLMModel(id: "anthropic/claude-sonnet-4-5", name: "Claude Sonnet 4.5", provider: "Anthropic", inPrice: 774, outPrice: 3866, contextLimit: 200_000),
        LLMModel(id: "openai/gpt-4o-mini-search-preview", name: "GPT-4o mini · Поиск 🌐", provider: "OpenAI", inPrice: 39, outPrice: 155, contextLimit: 128_000, web: true, supportsTemperature: false),
        LLMModel(id: "openai/gpt-4o-search-preview", name: "GPT-4o · Поиск 🌐", provider: "OpenAI", inPrice: 645, outPrice: 2577, contextLimit: 128_000, web: true, supportsTemperature: false)
    ]

    static let defaultModel = all[0]

    static func by(id: String?) -> LLMModel {
        all.first { $0.id == id } ?? defaultModel
    }
}
