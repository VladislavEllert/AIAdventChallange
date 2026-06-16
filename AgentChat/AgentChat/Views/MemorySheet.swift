import SwiftUI

/// Единый UI для трёх слоёв памяти текущего чата.
struct MemorySheet: View {
    var vm: ChatViewModel

    @AppStorage("globalProfile") private var globalProfile = ""
    @State private var showProfileEditor = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                // MARK: Краткосрочная
                Section {
                    HStack {
                        Image(systemName: "clock")
                            .foregroundStyle(.blue)
                        Text("В окне: \(vm.windowMessageCount) сообщ.")
                            .font(.subheadline)
                    }
                    if vm.hasSummary, let summary = vm.currentSummary {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Сжатый диалог", systemImage: "rectangle.compress.vertical")
                                .font(.caption.bold())
                                .foregroundStyle(.secondary)
                            Text(summary)
                                .font(.caption)
                                .foregroundStyle(.primary)
                        }
                        .padding(.vertical, 2)
                    } else {
                        Text("Summary пока нет — диалог короткий")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } header: {
                    Label("Краткосрочная (текущий диалог)", systemImage: "clock")
                }

                // MARK: Рабочая
                Section {
                    if vm.isUpdatingTaskContext {
                        HStack(spacing: 8) {
                            ProgressView().scaleEffect(0.8)
                            Text("Извлекаю контекст задачи…")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } else if let ctx = vm.taskContext, !ctx.isEmpty {
                        Text(ctx)
                            .font(.callout)
                    } else {
                        Text("Появится после первых сообщений о задаче")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } header: {
                    Label("Рабочая (текущая задача)", systemImage: "gearshape")
                }

                // MARK: Долговременная
                Section {
                    if globalProfile.isEmpty {
                        Text("Не заполнен. Нажми «Редактировать» чтобы добавить.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        Text(globalProfile)
                            .font(.callout)
                    }
                    Button {
                        showProfileEditor = true
                    } label: {
                        Label("Редактировать профиль", systemImage: "pencil")
                            .font(.subheadline)
                    }
                } header: {
                    Label("Долговременная (глобальный профиль)", systemImage: "person.text.rectangle")
                } footer: {
                    Text("Общий для всех агентов и чатов. Добавляй через long-press на сообщение.")
                        .font(.caption2)
                }
            }
            .navigationTitle("Память")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark")
                    }
                }
            }
            .sheet(isPresented: $showProfileEditor) {
                GlobalProfileSheet()
            }
        }
    }
}
