import SwiftUI
import SwiftData

struct ChatListView: View {
    @Query private var chats: [ChatSession]
    @Environment(\.modelContext) private var context

    let currentID: UUID?
    let onSelect: (ChatSession) -> Void
    let onNew: () -> Void
    let onClose: () -> Void
    let onDeleted: (UUID) -> Void

    init(
        agentID: UUID,
        currentID: UUID?,
        onSelect: @escaping (ChatSession) -> Void,
        onNew: @escaping () -> Void,
        onClose: @escaping () -> Void,
        onDeleted: @escaping (UUID) -> Void
    ) {
        self.currentID = currentID
        self.onSelect = onSelect
        self.onNew = onNew
        self.onClose = onClose
        self.onDeleted = onDeleted
        let aid: UUID? = agentID
        _chats = Query(
            filter: #Predicate<ChatSession> { $0.agentID == aid },
            sort: \.createdAt,
            order: .reverse
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Button(action: onClose) {
                    Label("Закрыть", systemImage: "xmark")
                        .font(.subheadline)
                }
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.top, 16)

            Spacer().frame(height: 28)

            Button(action: onNew) {
                HStack(spacing: 8) {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 20))
                    Text("Новый чат")
                        .fontWeight(.semibold)
                    Spacer()
                }
                .foregroundStyle(Color.accentColor)
                .padding(.vertical, 12)
                .padding(.horizontal, 14)
                .background(
                    Color.accentColor.opacity(0.12),
                    in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                )
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 14)

            Text("Чаты")
                .font(.headline)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 16)
                .padding(.bottom, 4)

            List {
                ForEach(chats) { chat in
                    Button {
                        onSelect(chat)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(chat.title.isEmpty ? "Без названия" : chat.title)
                                .font(.body)
                                .foregroundStyle(.primary)
                                .lineLimit(1)
                            Text(chat.createdAt, format: .dateTime.day().month().hour().minute())
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .listRowBackground(
                        chat.id == currentID
                            ? Color.accentColor.opacity(0.12)
                            : Color(.systemGroupedBackground)
                    )
                    .contextMenu {
                        Button(role: .destructive) {
                            delete(chat)
                        } label: {
                            Label("Удалить чат", systemImage: "trash")
                        }
                    }
                }
                .onDelete { offsets in
                    offsets.map { chats[$0] }.forEach(delete)
                }
            }
            .listStyle(.plain)
            .overlay {
                if chats.isEmpty {
                    Text("Чатов пока нет")
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func delete(_ chat: ChatSession) {
        let id = chat.id
        context.delete(chat)
        onDeleted(id)
    }
}
