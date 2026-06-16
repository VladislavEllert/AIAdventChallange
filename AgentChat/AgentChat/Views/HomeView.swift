import SwiftUI
import SwiftData

struct HomeView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \AgentProfile.createdAt, order: .forward) private var agents: [AgentProfile]

    @State private var showCreate = false
    @State private var showSettings = false
    @State private var editingAgent: AgentProfile?

    private let columns = [
        GridItem(.flexible(), spacing: 14),
        GridItem(.flexible(), spacing: 14)
    ]

    private var visibleAgents: [AgentProfile] {
        agents.filter { !$0.isCourseTest }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                AmbientBackground()

                ScrollView {
                    LazyVGrid(columns: columns, spacing: 14) {
                        ForEach(visibleAgents) { agent in
                            NavigationLink(value: agent) {
                                AgentCard(agent: agent)
                            }
                            .buttonStyle(PressableCardStyle())
                            .contextMenu {
                                Button {
                                    editingAgent = agent
                                } label: {
                                    Label("Изменить", systemImage: "pencil")
                                }
                                if !agent.isBuiltIn {
                                    Button(role: .destructive) {
                                        deleteAgent(agent)
                                    } label: {
                                        Label("Удалить агента", systemImage: "trash")
                                    }
                                }
                            }
                        }

                        Button {
                            showCreate = true
                        } label: {
                            CreateAgentCard()
                        }
                        .buttonStyle(PressableCardStyle())
                    }
                    .padding(16)
                }
            }
            .navigationTitle("Агенты")
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .navigationDestination(for: AgentProfile.self) { agent in
                ChatView(agentProfile: agent)
            }
            .sheet(isPresented: $showCreate) { AgentEditorView() }
            .sheet(item: $editingAgent) { AgentEditorView(agent: $0) }
            .sheet(isPresented: $showSettings) { SettingsView() }
            .onAppear { AgentProfile.ensureBuiltIns(context) }
        }
    }

    private func deleteAgent(_ agent: AgentProfile) {
        let agentID: UUID? = agent.id
        if let chats = try? context.fetch(
            FetchDescriptor<ChatSession>(predicate: #Predicate { $0.agentID == agentID })
        ) {
            chats.forEach { context.delete($0) }
        }
        context.delete(agent)
    }
}

struct PressableCardStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
            .opacity(configuration.isPressed ? 0.9 : 1)
            .animation(.easeOut(duration: 0.16), value: configuration.isPressed)
    }
}

struct AgentCard: View {
    let agent: AgentProfile

    var body: some View {
        VStack(spacing: 12) {
            Text(agent.emoji)
                .font(.system(size: 44))
            Text(agent.name)
                .font(.headline)
                .foregroundStyle(.primary)
                .lineLimit(1)
            Text(agent.isCourseTest ? agent.strategy.displayName : (agent.isBuiltIn ? "Встроенный" : "Свой"))
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 156)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 26, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.06), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.10), radius: 12, y: 6)
    }
}

struct CreateAgentCard: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "plus")
                .font(.system(size: 34, weight: .light))
            Text("Создать агента")
                .font(.subheadline)
        }
        .foregroundStyle(.secondary)
        .frame(maxWidth: .infinity)
        .frame(height: 156)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 26, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .strokeBorder(style: StrokeStyle(lineWidth: 1.2, dash: [6]))
                .foregroundStyle(Color.primary.opacity(0.15))
        )
    }
}
