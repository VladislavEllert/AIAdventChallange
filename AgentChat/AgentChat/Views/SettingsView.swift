import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("themeMode") private var themeRaw = ThemeMode.system.rawValue
    @AppStorage("selectedModelID") private var selectedModelID = LLMModel.defaultModel.id
    @AppStorage("demoWindowSize") private var demoWindowSize = 12
    @AppStorage("demoLimitEnabled") private var demoLimitEnabled = false
    @AppStorage("demoLimitValue") private var demoLimitValue = 2000
    @AppStorage("compressionLevel") private var compressionLevelRaw = CompressionLevel.default.rawValue
    @AppStorage("autoMemoryEnabled") private var autoMemoryEnabled = true
    @AppStorage("showTokenMeta") private var showTokenMeta = true
    @AppStorage("showCompactionInfo") private var showCompactionInfo = true
    @AppStorage("showContextHUD") private var showContextHUD = true

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
                compressionSection
                memorySection
                demoSection
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
            LabeledContent("Лимит контекста", value: "\(selectedModel.contextLimit) ток.")
        } header: {
            Text("Модель")
        } footer: {
            Text("\(selectedModel.name): \(selectedModel.priceFull). Цена показывает, сколько стоит 1М входных/выходных токенов в рублях ProxyAPI. Лимит контекста — сколько токенов модель держит в окне.")
        }
    }

    private var compressionSection: some View {
        Section {
            Picker("Степень сжатия", selection: $compressionLevelRaw) {
                ForEach(CompressionLevel.allCases) { level in
                    Text(level.label).tag(level.rawValue)
                }
            }
            .pickerStyle(.navigationLink)
        } header: {
            Text("Сжатие контекста")
        } footer: {
            Text("Когда контекст подходит к лимиту (или вручную «Сжать контекст»), старое начало диалога сжимается в summary, а свежие сообщения остаются. Чем жёстче — тем меньше свежих оставляем и сильнее экономим токены, но больше деталей теряется.")
        }
    }

    private var memorySection: some View {
        Section {
            Toggle("Авто-память (факты)", isOn: $autoMemoryEnabled)
        } header: {
            Text("Память")
        } footer: {
            Text("Включено: при выходе из чата агент извлекает долгие факты о тебе. Выключи для чистого демо переполнения — тогда тестовые данные из чата не попадут в долгую память и не будут «спасать» от забывания.")
        }
    }

    private var demoSection: some View {
        Section {
            Toggle("Токены под сообщениями", isOn: $showTokenMeta)
            Toggle("Информация о сжатии", isOn: $showCompactionInfo)
            Toggle("Метр контекста (панель)", isOn: $showContextHUD)
            Stepper("Окно: последние \(demoWindowSize) сообщ.", value: $demoWindowSize, in: 2...20)
            Toggle("Демо-лимит контекста", isOn: $demoLimitEnabled)
            if demoLimitEnabled {
                Stepper("Лимит: \(demoLimitValue) ток.", value: $demoLimitValue, in: 500...20000, step: 500)
            }
        } header: {
            Text("Дополнительные параметры")
        } footer: {
            Text("Тумблеры показа (день-8): токены под сообщениями, плашки сжатия, панель контекста — можно прятать. Окно и демо-лимит — учебные: маленькое окно → старое быстро уезжает (видно забывание); демо-лимит → искусственное переполнение, чтобы увидеть, что ломается, не упираясь в реальный лимит модели.")
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
