import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("themeMode") private var themeRaw = ThemeMode.system.rawValue
    @AppStorage("selectedModelID") private var selectedModelID = LLMModel.defaultModel.id

    @State private var keyInput: String = ""
    @State private var keyVersion = 0
    @State private var savedFlash = false

    private var maskedKey: String? {
        _ = keyVersion
        return APIKeyStore.shared.maskedKey
    }

    private var selectedModel: LLMModel { LLMModel.by(id: selectedModelID) }

    var body: some View {
        NavigationStack {
            Form {
                apiKeySection
                modelSection
                themeSection
            }
            .navigationTitle("Настройки")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Готово") { dismiss() }
                }
            }
            .alert("Ключ сохранён", isPresented: $savedFlash) {
                Button("Ок", role: .cancel) {}
            }
            .preferredColorScheme(ThemeMode(rawValue: themeRaw)?.colorScheme ?? nil)
        }
    }

    private var apiKeySection: some View {
        Section {
            if let masked = maskedKey {
                LabeledContent("Текущий ключ", value: masked)
                    .monospaced()
            }
            SecureField(maskedKey == nil ? "sk-… ключ ProxyAPI" : "Новый ключ (заменить)", text: $keyInput)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            Button("Сохранить ключ") {
                if APIKeyStore.shared.save(keyInput) {
                    keyInput = ""
                    keyVersion += 1
                    savedFlash = true
                }
            }
            .disabled(keyInput.trimmingCharacters(in: .whitespaces).isEmpty)
            if maskedKey != nil {
                Button("Удалить ключ", role: .destructive) {
                    APIKeyStore.shared.delete()
                    keyVersion += 1
                }
            }
        } header: {
            Text("API-ключ")
        } footer: {
            Text("Ключ хранится только в Keychain устройства, не в коде. Показаны 3 первых и 3 последних символа.")
        }
    }

    private var modelSection: some View {
        Section {
            Picker("Модель", selection: $selectedModelID) {
                ForEach(LLMModel.all) { model in
                    Text("\(model.name) · \(model.priceShort)").tag(model.id)
                }
            }
            .pickerStyle(.navigationLink)

            LabeledContent("Провайдер", value: selectedModel.provider)
            LabeledContent("Цена", value: selectedModel.priceShort)
        } header: {
            Text("Модель")
        } footer: {
            Text("\(selectedModel.name): \(selectedModel.priceFull). Цена показывает, сколько стоит 1М входных/выходных токенов в рублях ProxyAPI.")
        }
    }

    private var themeSection: some View {
        Section("Тема") {
            Picker("Оформление", selection: $themeRaw) {
                ForEach(ThemeMode.allCases) { mode in
                    Text(mode.label).tag(mode.rawValue)
                }
            }
            .pickerStyle(.segmented)
        }
    }
}

#Preview {
    SettingsView()
}
