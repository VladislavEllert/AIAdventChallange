import SwiftUI

/// Редактор долговременной памяти (глобальный профиль).
/// Общий для всех агентов и чатов. Инжектируется в system prompt каждого запроса.
struct GlobalProfileSheet: View {
    @AppStorage("globalProfile") private var globalProfile = ""
    @Environment(\.dismiss) private var dismiss
    @State private var draft = ""

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 0) {
                Text("Что агент должен знать о тебе всегда: стек, предпочтения, правила, цели.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 16)
                    .padding(.top, 12)
                    .padding(.bottom, 8)

                TextEditor(text: $draft)
                    .font(.body)
                    .padding(.horizontal, 12)
            }
            .navigationTitle("Долговременная память")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Отмена") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Сохранить") {
                        globalProfile = draft.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
            .onAppear { draft = globalProfile }
        }
    }
}
