import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    private var isUser: Bool { message.role == .user }

    var body: some View {
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
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
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
