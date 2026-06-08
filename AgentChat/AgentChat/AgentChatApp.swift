import SwiftUI
import SwiftData

@main
struct AgentChatApp: App {
    @AppStorage("themeMode") private var themeRaw = ThemeMode.system.rawValue

    var body: some Scene {
        WindowGroup {
            HomeView()
                .preferredColorScheme(ThemeMode(rawValue: themeRaw)?.colorScheme ?? nil)
        }
        .modelContainer(for: [AgentProfile.self, ChatSession.self, StoredMessage.self])
    }
}
