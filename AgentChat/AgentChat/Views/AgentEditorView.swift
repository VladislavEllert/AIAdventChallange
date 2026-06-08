import SwiftUI
import SwiftData

struct AgentEditorView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss

    private let agent: AgentProfile?

    @State private var name: String
    @State private var emoji: String
    @State private var systemPrompt: String

    init(agent: AgentProfile? = nil) {
        self.agent = agent
        _name = State(initialValue: agent?.name ?? "")
        _emoji = State(initialValue: agent?.emoji ?? "🤖")
        _systemPrompt = State(initialValue: agent?.systemPrompt ?? "")
    }

    private var isEditing: Bool { agent != nil }

    private var canSave: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty &&
        !systemPrompt.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Имя") {
                    TextField("Например: Шеф-повар", text: $name)
                }
                Section("Эмодзи") {
                    TextField("🤖", text: $emoji)
                        .onChange(of: emoji) {
                            if let last = emoji.last { emoji = String(last) } else { emoji = "" }
                        }
                }
                Section {
                    TextEditor(text: $systemPrompt)
                        .frame(minHeight: 160)
                } header: {
                    Text("Системный промпт (инструкция)")
                } footer: {
                    Text("Опиши, кто этот агент и как себя ведёт. Это его личность.")
                }
            }
            .navigationTitle(isEditing ? "Редактировать" : "Новый агент")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Отмена") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button(isEditing ? "Сохранить" : "Создать") { save() }
                        .disabled(!canSave)
                }
            }
        }
    }

    private func save() {
        let finalName = name.trimmingCharacters(in: .whitespaces)
        let finalEmoji = emoji.isEmpty ? "🤖" : emoji
        let finalPrompt = systemPrompt.trimmingCharacters(in: .whitespacesAndNewlines)

        if let agent {
            agent.name = finalName
            agent.emoji = finalEmoji
            agent.systemPrompt = finalPrompt
        } else {
            context.insert(AgentProfile(
                name: finalName,
                emoji: finalEmoji,
                systemPrompt: finalPrompt,
                isBuiltIn: false
            ))
        }
        dismiss()
    }
}
