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

/// Долгая память агента: список фактов о пользователе (добавить/изменить/удалить/почистить).
private struct FactsSection: View {
    @Bindable var agent: AgentProfile
    @State private var newFact = ""
    @State private var editIndex: Int?
    @State private var editText = ""
    @State private var isCleaning = false
    private let memory = MemoryService()

    var body: some View {
        Section {
            ForEach(Array(agent.facts.enumerated()), id: \.offset) { index, fact in
                Text(fact)
                    .contextMenu {
                        Button { startEdit(index, fact) } label: {
                            Label("Изменить", systemImage: "pencil")
                        }
                        Button(role: .destructive) { delete(index) } label: {
                            Label("Удалить", systemImage: "trash")
                        }
                    }
            }
            .onDelete { agent.facts.remove(atOffsets: $0) }

            HStack {
                TextField("Добавить факт", text: $newFact)
                Button {
                    add()
                } label: {
                    Image(systemName: "plus.circle.fill")
                }
                .disabled(newFact.trimmingCharacters(in: .whitespaces).isEmpty)
            }

            if agent.facts.count > 1 {
                Button {
                    clean()
                } label: {
                    Label(isCleaning ? "Чищу…" : "Почистить память (ИИ)", systemImage: "sparkles")
                }
                .disabled(isCleaning)
            }
        } header: {
            Text("Память (факты о пользователе)")
        } footer: {
            Text("Помнит во всех чатах. Зажми факт → изменить/удалить. «Почистить» объединит дубли и уберёт устаревшее.")
        }
        .alert("Изменить факт", isPresented: editingBinding) {
            TextField("Факт", text: $editText)
            Button("Сохранить") { saveEdit() }
            Button("Отмена", role: .cancel) { editIndex = nil }
        }
    }

    private var editingBinding: Binding<Bool> {
        Binding(get: { editIndex != nil }, set: { if !$0 { editIndex = nil } })
    }

    private func add() {
        let fact = newFact.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !fact.isEmpty else { return }
        if !agent.facts.contains(where: { $0.lowercased() == fact.lowercased() }) {
            agent.facts.append(fact)
        }
        newFact = ""
    }

    private func delete(_ index: Int) {
        guard agent.facts.indices.contains(index) else { return }
        agent.facts.remove(at: index)
    }

    private func startEdit(_ index: Int, _ fact: String) {
        editIndex = index
        editText = fact
    }

    private func saveEdit() {
        guard let index = editIndex, agent.facts.indices.contains(index) else { return }
        let text = editText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty { agent.facts[index] = text }
        editIndex = nil
    }

    private func clean() {
        isCleaning = true
        Task {
            let cleaned = (try? await memory.consolidate(facts: agent.facts)) ?? agent.facts
            agent.facts = cleaned
            isCleaning = false
        }
    }
}
