import Foundation

/// Степень компактации контекста: сколько свежих сообщений окна ОСТАВЛЯЕМ,
/// остальное (старое начало) сжимаем в summary. Меньше оставляем → жёстче сжатие.
enum CompressionLevel: String, CaseIterable, Identifiable {
    case hard, medium, light

    var id: String { rawValue }

    /// Доля окна, которую оставляем как есть (свежие сообщения).
    var keepFraction: Double {
        switch self {
        case .hard:   return 0.2
        case .medium: return 0.5
        case .light:  return 0.7
        }
    }

    var label: String {
        switch self {
        case .hard:   return "Жёсткая · оставить 20%"
        case .medium: return "Средняя · оставить 50%"
        case .light:  return "Лёгкая · оставить 70%"
        }
    }

    var short: String {
        switch self {
        case .hard:   return "20%"
        case .medium: return "50%"
        case .light:  return "70%"
        }
    }

    /// Бюджет длины самой выжимки (слов): жёстче → короче summary → меньше токенов.
    var summaryWords: Int {
        switch self {
        case .hard:   return 40
        case .medium: return 80
        case .light:  return 120
        }
    }

    static let `default` = CompressionLevel.medium
}
