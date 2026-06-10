import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    @AppStorage("showTokenMeta") private var showTokenMeta = true
    @AppStorage("showCompactionInfo") private var showCompactionInfo = true

    private var isUser: Bool { message.role == .user }
    private var isSystem: Bool { message.role == .system }
    private var isEmptyPlaceholder: Bool { message.role == .assistant && message.content.isEmpty && message.imageData == nil }

    var body: some View {
        if isEmptyPlaceholder {
            EmptyView()   // плейсхолдер стрима до первой дельты — крутилку рисует ChatView
        } else if isSystem {
            if showCompactionInfo { systemPill } else { EmptyView() }
        } else {
            VStack(alignment: isUser ? .trailing : .leading, spacing: 3) {
                bubble
                meta
            }
            .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
        }
    }

    /// Системное событие (например компактация) — центрированная плашка.
    private var systemPill: some View {
        Text(message.content)
            .font(.caption)
            .foregroundStyle(.secondary)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial, in: Capsule())
            .frame(maxWidth: .infinity, alignment: .center)
    }

    private var bubble: some View {
        HStack {
            if isUser { Spacer(minLength: 40) }

            VStack(alignment: .leading, spacing: 6) {
                if let data = message.imageData, let uiImage = UIImage(data: data) {
                    Image(uiImage: uiImage)
                        .resizable()
                        .scaledToFill()
                        .frame(maxWidth: 220, maxHeight: 220)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                if !message.content.isEmpty {
                    if isUser {
                        Text(message.content)
                            .font(.body)
                            .foregroundStyle(Color.white)
                            .textSelection(.enabled)
                    } else {
                        MarkdownText(text: message.content)
                            .font(.body)
                            .foregroundStyle(Color.primary)
                            .tint(.accentColor)
                            .textSelection(.enabled)
                    }
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(
                isUser ? AnyShapeStyle(Color.accentColor)
                       : AnyShapeStyle(.ultraThinMaterial),
                in: RoundedRectangle(cornerRadius: 18, style: .continuous)
            )

            if !isUser { Spacer(minLength: 40) }
        }
    }

    @ViewBuilder private var meta: some View {
        if !showTokenMeta {
            EmptyView()
        } else if isUser {
            if !message.content.isEmpty {
                metaText("≈\(TokenEstimator.estimate(message.content)) ток.")
            }
        } else if let u = message.usage {
            let model = LLMModel.by(id: message.modelID)
            HStack(spacing: 7) {
                Text("↑\(u.promptTokens)")
                Text("↓\(u.completionTokens)")
                if let r = u.reasoningTokens, r > 0 { Text("🧠\(r)") }
                Text("Σ\(u.totalTokens)")
                Text(String(format: "₽%.4f", model.cost(u)))
                if let t = message.responseTime { Text(String(format: "%.1fс", t)) }
            }
            .font(.system(.caption2, design: .monospaced))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 6)
        }
    }

    private func metaText(_ s: String) -> some View {
        Text(s)
            .font(.system(.caption2, design: .monospaced))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 6)
    }
}

struct TypingBubble: View {
    var body: some View {
        HStack {
            ProgressView()
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(
                    .ultraThinMaterial,
                    in: RoundedRectangle(cornerRadius: 18, style: .continuous)
                )
            Spacer(minLength: 40)
        }
    }
}
