import SwiftUI

/// Лёгкий рендер markdown для ответов модели: заголовки (#), списки (-, 1.),
/// блоки кода (```), inline **жирный**/*курсив*/`код`/ссылки.
struct MarkdownText: View {
    let text: String

    var body: some View {
        let blocks = Self.parse(text)
        VStack(alignment: .leading, spacing: 6) {
            ForEach(blocks.indices, id: \.self) { i in
                view(for: blocks[i])
            }
        }
    }

    @ViewBuilder
    private func view(for block: Block) -> some View {
        switch block {
        case .heading(let level, let s):
            inline(s).font(headingFont(level))
        case .bullet(let s):
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text("•")
                inline(s)
            }
        case .ordered(let num, let s):
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text("\(num).")
                inline(s)
            }
        case .paragraph(let s):
            inline(s).frame(maxWidth: .infinity, alignment: .leading)
        case .code(let s):
            Text(s)
                .font(.system(.callout, design: .monospaced))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color(.tertiarySystemFill), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
    }

    private func inline(_ s: String) -> Text {
        if let attr = try? AttributedString(
            markdown: s,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            return Text(attr)
        }
        return Text(s)
    }

    private func headingFont(_ level: Int) -> Font {
        switch level {
        case 1: return .title3.bold()
        case 2: return .headline
        default: return .subheadline.bold()
        }
    }

    enum Block {
        case heading(Int, String)
        case bullet(String)
        case ordered(Int, String)
        case paragraph(String)
        case code(String)
    }

    static func parse(_ text: String) -> [Block] {
        var blocks: [Block] = []
        var inCode = false
        var codeLines: [String] = []

        for line in text.components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            if trimmed.hasPrefix("```") {
                if inCode {
                    blocks.append(.code(codeLines.joined(separator: "\n")))
                    codeLines = []
                    inCode = false
                } else {
                    inCode = true
                }
                continue
            }
            if inCode { codeLines.append(line); continue }
            if trimmed.isEmpty { continue }

            if let h = heading(trimmed) {
                blocks.append(.heading(h.0, h.1))
            } else if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") {
                blocks.append(.bullet(String(trimmed.dropFirst(2))))
            } else if let ord = ordered(trimmed) {
                blocks.append(.ordered(ord.0, ord.1))
            } else {
                blocks.append(.paragraph(trimmed))
            }
        }
        if inCode, !codeLines.isEmpty {
            blocks.append(.code(codeLines.joined(separator: "\n")))
        }
        return blocks
    }

    private static func heading(_ s: String) -> (Int, String)? {
        var level = 0
        var idx = s.startIndex
        while idx < s.endIndex, s[idx] == "#" {
            level += 1
            idx = s.index(after: idx)
        }
        guard level > 0, level <= 6, idx < s.endIndex, s[idx] == " " else { return nil }
        return (level, String(s[s.index(after: idx)...]))
    }

    private static func ordered(_ s: String) -> (Int, String)? {
        guard let dot = s.firstIndex(of: "."),
              let num = Int(s[s.startIndex..<dot]),
              s.index(after: dot) < s.endIndex,
              s[s.index(after: dot)] == " " else { return nil }
        return (num, String(s[s.index(dot, offsetBy: 2)...]))
    }
}
