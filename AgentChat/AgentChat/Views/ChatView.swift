import SwiftUI
import PhotosUI
import SwiftData

struct ChatView: View {
    let agentProfile: AgentProfile

    private enum ActiveSheet: Identifiable {
        case settings
        case export(String)
        case stats
        case memory
        var id: Int {
            switch self {
            case .settings: return 0
            case .export: return 1
            case .stats: return 2
            case .memory: return 3
            }
        }
    }

    @Environment(\.modelContext) private var context
    @AppStorage("showContextHUD") private var showContextHUD = true
    @State private var vm = ChatViewModel()
    @State private var activeSheet: ActiveSheet?
    @State private var showChats = false
    @State private var photoItem: PhotosPickerItem?
    @State private var draft = ""

    private var canSend: Bool {
        let hasText = !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        return (hasText || vm.attachedImage != nil) && !vm.isLoading
    }

    private func submit() {
        guard canSend else { return }
        let text = draft
        draft = ""
        vm.send(text: text)
    }

    var body: some View {
        GeometryReader { geo in
            let drawerWidth = min(geo.size.width * 0.84, 340)
            ZStack(alignment: .leading) {
                VStack(spacing: 0) {
                    if vm.isTestAgent { strategyBar }
                    messagesArea
                    Divider()
                    if showContextHUD { contextHUD }
                    inputBar
                }
                .background(AmbientBackground())
                .navigationTitle(vm.agentTitle)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button { showChats = true } label: {
                            Image(systemName: "line.3.horizontal")
                        }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button { activeSheet = .memory } label: {
                            Image(systemName: "brain")
                        }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Menu {
                            Button { activeSheet = .stats } label: {
                                Label("Статистика чата (токены)", systemImage: "number")
                            }
                            if !vm.isTestAgent {
                                Button { Task { await vm.compactNow(auto: false) } } label: {
                                    Label("Сжать контекст", systemImage: "rectangle.compress.vertical")
                                }
                            }
                            Button {
                                activeSheet = .export(vm.exportJSON())
                            } label: {
                                Label("Экспорт памяти (JSON)", systemImage: "curlybraces")
                            }
                            Button { activeSheet = .settings } label: {
                                Label("Настройки", systemImage: "gearshape")
                            }
                        } label: {
                            Image(systemName: "ellipsis.circle")
                        }
                    }
                }
                .sheet(item: $activeSheet) { sheet in
                    switch sheet {
                    case .settings: SettingsView()
                    case .export(let json): MemoryExportSheet(json: json)
                    case .stats: ChatStatsSheet(vm: vm)
                    case .memory: MemorySheet(vm: vm)
                    }
                }
                .onAppear {
                    vm.attach(context, profile: agentProfile)
                    if !vm.hasKey { activeSheet = .settings }
                }
                .onDisappear { vm.extractFactsOnLeave() }
                .onChange(of: photoItem) { Task { await loadPhoto() } }

                if showChats {
                    Color.black.opacity(0.35)
                        .ignoresSafeArea()
                        .onTapGesture { closeDrawer() }
                }

                ChatListView(
                    agentID: agentProfile.id,
                    currentID: vm.currentChatID,
                    onSelect: { vm.open($0); closeDrawer() },
                    onNew: { vm.newChat(); closeDrawer() },
                    onClose: { closeDrawer() },
                    onDeleted: { vm.chatDeleted($0) }
                )
                .frame(width: drawerWidth, alignment: .leading)
                .frame(maxHeight: .infinity)
                .background(Color(.systemGroupedBackground))
                .offset(x: showChats ? 0 : -(drawerWidth + 12))
                .shadow(color: .black.opacity(showChats ? 0.2 : 0), radius: 10, x: 2, y: 0)
            }
            .animation(.easeInOut(duration: 0.25), value: showChats)
            .simultaneousGesture(
                DragGesture(minimumDistance: 20)
                    .onEnded { value in
                        let dx = value.translation.width
                        let dy = abs(value.translation.height)
                        guard abs(dx) > dy else { return }   // горизонтальный свайп
                        if !showChats, value.startLocation.x < 40, dx > 60 {
                            showChats = true
                        } else if showChats, dx < -60 {
                            showChats = false
                        }
                    }
            )
        }
    }

    private func closeDrawer() {
        showChats = false
    }

    private var messagesArea: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    if vm.messages.isEmpty {
                        emptyState
                    }
                    ForEach(vm.messages) { message in
                        MessageBubble(message: message)
                            .id(message.id)
                            .contextMenu {
                                if !message.content.isEmpty, message.role != .system {
                                    if vm.strategyKind == .branching {
                                        Button {
                                            vm.forkBranch(after: message)
                                        } label: {
                                            Label("Ветка отсюда", systemImage: "arrow.triangle.branch")
                                        }
                                    } else if !vm.isTestAgent {
                                        Button {
                                            vm.remember(message.content)
                                        } label: {
                                            Label("Запомнить (факт агента)", systemImage: "brain")
                                        }
                                    }
                                    // День-11: сохранить в глобальный профиль (долговременная память).
                                    Button {
                                        vm.saveToProfile(message.content)
                                    } label: {
                                        Label("В долговременную память", systemImage: "pin")
                                    }
                                }
                            }
                    }
                    if isAwaitingFirstToken {
                        TypingBubble().id("typing")
                    }
                    if let error = vm.errorText {
                        errorBanner(error)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 16)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: vm.messages.count) { scrollToBottom(proxy) }
            .onChange(of: vm.isLoading) { scrollToBottom(proxy) }
            .onChange(of: vm.messages.last?.content) { scrollToBottom(proxy) }
        }
    }

    /// Крутилку показываем только пока стрим не выдал первый токен (потом растёт сам пузырь).
    private var isAwaitingFirstToken: Bool {
        guard vm.isLoading else { return false }
        let streaming = vm.messages.first(where: { $0.id == vm.streamingID })
        return streaming?.content.isEmpty ?? true
    }

    private func short(_ n: Int) -> String {
        if n >= 1_000_000 { return String(format: "%.1fM", Double(n) / 1_000_000) }
        if n >= 1_000 { return "\(n / 1000)k" }
        return "\(n)"
    }

    // MARK: - Полоса стратегии (день-10, тест-агенты)

    private var strategyIcon: String {
        switch vm.strategyKind {
        case .standard: return "tray.full"
        case .slidingWindow: return "rectangle.righthalf.inset.filled"
        case .stickyFacts: return "list.bullet.rectangle"
        case .branching: return "arrow.triangle.branch"
        }
    }

    private var strategyBar: some View {
        VStack(spacing: 6) {
            HStack(spacing: 6) {
                Image(systemName: strategyIcon)
                    .font(.caption)
                    .foregroundStyle(Color.accentColor)
                Text(vm.strategyKind.displayName)
                    .font(.caption.bold())
                Text("· \(vm.strategyKind.shortHint)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Spacer()
                if vm.strategyKind == .stickyFacts {
                    if vm.isUpdatingFacts {
                        ProgressView().scaleEffect(0.7)
                    } else {
                        Text("\(vm.stickyFacts.count) фактов")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            if vm.strategyKind == .stickyFacts, !vm.stickyFacts.isEmpty {
                factsStrip
            }
            if vm.strategyKind == .branching {
                branchChips
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private var factsStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(vm.stickyFacts) { fact in
                    Text("\(fact.key): \(fact.value)")
                        .font(.caption2)
                        .lineLimit(1)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color(.secondarySystemBackground), in: Capsule())
                }
            }
        }
    }

    private var branchChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(vm.branchChips) { chip in
                    Button {
                        vm.switchBranch(to: chip.id)
                    } label: {
                        Text("\(chip.isMain ? "⭐ " : "")\(chip.name) · \(chip.messageCount)")
                            .font(.caption2.bold())
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(
                                chip.isActive ? Color.accentColor : Color(.secondarySystemBackground),
                                in: Capsule()
                            )
                            .foregroundStyle(chip.isActive ? .white : .primary)
                    }
                    .buttonStyle(.plain)
                    .contextMenu {
                        if !chip.isMain {
                            Button {
                                vm.makeBranchMain(chip.id)
                            } label: {
                                Label("Сделать основной", systemImage: "star")
                            }
                        }
                        if vm.branchChips.count > 1 {
                            Button(role: .destructive) {
                                vm.deleteBranch(chip.id)
                            } label: {
                                Label("Удалить ветку", systemImage: "trash")
                            }
                        }
                    }
                }
            }
        }
    }

    private var contextHUD: some View {
        let fill = vm.contextFill
        let danger = fill > 0.9
        return VStack(spacing: 4) {
            HStack(spacing: 8) {
                Text("Контекст")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                ProgressView(value: fill)
                    .tint(danger ? .red : .accentColor)
                Text("\(short(vm.lastPromptTokens))/\(short(vm.effectiveContextLimit))")
                    .font(.system(.caption2, design: .monospaced))
                    .foregroundStyle(danger ? .red : .secondary)
                if vm.demoLimitEnabled {
                    Text("демо")
                        .font(.caption2.bold())
                        .foregroundStyle(.orange)
                }
            }
            HStack {
                Text("Диалог: Σ \(vm.sessionTokens) ток.")
                Spacer()
                Text(String(format: "₽ %.4f", vm.sessionCostRub))
            }
            .font(.system(.caption2, design: .monospaced))
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Text(agentProfile.emoji)
                .font(.system(size: 56))
            Text("Напиши \(agentProfile.name)")
                .font(.headline)
            Text("Он помнит весь диалог этого чата.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 80)
    }

    private func errorBanner(_ text: String) -> some View {
        Text(text)
            .font(.callout)
            .foregroundStyle(Color(.systemRed))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(
                Color(.systemRed).opacity(0.12),
                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
            )
    }

    private var inputBar: some View {
        VStack(spacing: 8) {
            if let data = vm.attachedImage, let uiImage = UIImage(data: data) {
                attachmentPreview(uiImage)
            }
            HStack(spacing: 10) {
                PhotosPicker(selection: $photoItem, matching: .images) {
                    Image(systemName: "paperclip")
                        .font(.system(size: 20, weight: .regular))
                        .foregroundStyle(Color.accentColor)
                        .frame(width: 34, height: 34)
                }

                TextField("Сообщение…", text: $draft, axis: .vertical)
                    .lineLimit(1...5)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 9)
                    .background(
                        Color(.secondarySystemBackground),
                        in: RoundedRectangle(cornerRadius: 20, style: .continuous)
                    )

                Button {
                    submit()
                } label: {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(width: 38, height: 38)
                        .background(
                            canSend ? Color.accentColor : Color(.systemGray3),
                            in: Circle()
                        )
                }
                .disabled(!canSend)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(.bar)
    }

    private func attachmentPreview(_ uiImage: UIImage) -> some View {
        HStack {
            ZStack(alignment: .topTrailing) {
                Image(uiImage: uiImage)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 64, height: 64)
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                Button {
                    vm.attachedImage = nil
                    photoItem = nil
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundStyle(.white, .black.opacity(0.6))
                }
                .offset(x: 6, y: -6)
            }
            Spacer()
        }
    }

    private func loadPhoto() async {
        guard let item = photoItem,
              let data = try? await item.loadTransferable(type: Data.self),
              let uiImage = UIImage(data: data) else { return }
        vm.attachedImage = Self.downscaledJPEG(uiImage)
    }

    private static func downscaledJPEG(_ image: UIImage, maxSide: CGFloat = 1024, quality: CGFloat = 0.6) -> Data? {
        let size = image.size
        let scale = min(1, maxSide / max(size.width, size.height))
        let target = CGSize(width: size.width * scale, height: size.height * scale)
        let renderer = UIGraphicsImageRenderer(size: target)
        let resized = renderer.image { _ in image.draw(in: CGRect(origin: .zero, size: target)) }
        return resized.jpegData(compressionQuality: quality)
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.2)) {
            if vm.isLoading {
                proxy.scrollTo("typing", anchor: .bottom)
            } else if let last = vm.messages.last {
                proxy.scrollTo(last.id, anchor: .bottom)
            }
        }
    }
}
