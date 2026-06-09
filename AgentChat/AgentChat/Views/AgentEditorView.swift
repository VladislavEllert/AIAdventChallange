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
        _emoji = State(initialValue: agent?.emoji ?? "")
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
                    TextField("Эмодзи", text: $emoji)
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

                if let agent {
                    FactsSection(agent: agent)
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
        let finalEmoji = emoji.isEmpty ? "🙂" : emoji
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

/// Долгая память агента: список фактов о пользователе (добавить/удалить).
private struct FactsSection: View {
    @Bindable var agent: AgentProfile
    @State private var newFact = ""

    var body: some View {
        Section {
            ForEach(agent.facts, id: \.self) { fact in
                Text(fact)
            }
            .onDelete { offsets in
                agent.facts.remove(atOffsets: offsets)
            }
            HStack {
                TextField("Добавить факт", text: $newFact)
                Button {
                    add()
                } label: {
                    Image(systemName: "plus.circle.fill")
                }
                .disabled(newFact.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        } header: {
            Text("Память (факты о пользователе)")
        } footer: {
            Text("Эти факты агент помнит во всех своих чатах. Наполняется вручную и авто-извлечением.")
        }
    }

    private func add() {
        let fact = newFact.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !fact.isEmpty else { return }
        if !agent.facts.contains(where: { $0.lowercased() == fact.lowercased() }) {
            agent.facts.append(fact)
        }
        newFact = ""
    }
}
