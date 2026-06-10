import SwiftUI

/// Наглядная статистика по токенам текущего чата + срез контекстного окна
/// (видно, как старые сообщения «уезжают» из окна — отсюда забывание/галлюцинации).
struct ChatStatsSheet: View {
    let vm: ChatViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Токены за чат") {
                    row("Вход (история+запросы)", "\(vm.sessionPromptTokens)")
                    row("Выход (ответы)", "\(vm.sessionCompletionTokens)")
                    if vm.sessionReasoningTokens > 0 {
                        row("из них «думанье» 🧠", "\(vm.sessionReasoningTokens)")
                    }
                    row("Всего", "\(vm.sessionTokens)")
                    row("Стоимость", String(format: "%.4f ₽", vm.sessionCostRub))
                    row("Ответов модели", "\(vm.answeredCount)")
                    if vm.avgResponseTime > 0 {
                        row("Среднее время ответа", String(format: "%.1f с", vm.avgResponseTime))
                    }
                }

                Section("Контекстное окно") {
                    row("Последний запрос (prompt)", "\(vm.lastPromptTokens) ток.")
                    row("Лимит окна", "\(vm.effectiveContextLimit) ток." + (vm.demoLimitEnabled ? " (демо)" : ""))
                    row("Заполнено", String(format: "%.1f%%", vm.contextFill * 100))
                    row("Размер окна (последние N)", "\(vm.windowSize) сообщ.")
                    row("В активном окне", "\(vm.windowMessageCount) сообщ.")
                    row("Сжато в summary", "\(vm.compressedMessageCount) сообщ.")
                    row("Есть summary", vm.hasSummary ? "да" : "нет")
                    if vm.trimmedCount > 0 {
                        row("Выкинуто из промпта (демо)", "\(vm.trimmedCount) сообщ.")
                    }
                }

                Section("Текущая summary (что помнится)") {
                    if let s = vm.currentSummary, !s.isEmpty {
                        Text(s)
                            .font(.footnote)
                            .textSelection(.enabled)
                    } else {
                        Text("Пока пусто — сжатия ещё не было.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Text("Каждый ход вся история пере-отправляется в модель → вход (prompt) и "
                         + "стоимость растут по ходу диалога. Когда старое уезжает за окно — оно "
                         + "сжимается в summary (с потерями) или теряется: модель начинает забывать "
                         + "и «галлюцинировать». В этом суть управления контекстом.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Статистика чата")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Готово") { dismiss() }
                }
            }
        }
    }

    private func row(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
            Spacer()
            Text(value)
                .font(.system(.body, design: .monospaced))
                .foregroundStyle(.secondary)
        }
    }
}
