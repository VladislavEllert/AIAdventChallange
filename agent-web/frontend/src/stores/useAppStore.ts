import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'system' | 'light' | 'dark'
type RightTab = 'memory' | 'task' | 'invariants' | 'profiles'

interface AppStore {
  theme: Theme
  setTheme: (t: Theme) => void
  activeSessionId: string | null
  setActiveSessionId: (id: string | null) => void
  activeModel: string
  setActiveModel: (m: string) => void
  activeAgentId: string | null
  activeAgentPersona: string
  setActiveAgent: (id: string | null, persona: string) => void
  activeProfileName: string | null
  setActiveProfileName: (name: string | null) => void
  sidebarOpen: boolean
  toggleSidebar: () => void
  rightPanelOpen: boolean
  toggleRightPanel: () => void
  rightPanelTab: RightTab
  setRightPanelTab: (t: RightTab) => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme }),
      activeSessionId: null,
      setActiveSessionId: (id) => set({ activeSessionId: id }),
      activeModel: 'openai/gpt-4o-mini',
      setActiveModel: (m) => set({ activeModel: m }),
      activeAgentId: null,
      activeAgentPersona: '',
      setActiveAgent: (id, persona) => set({ activeAgentId: id, activeAgentPersona: persona }),
      activeProfileName: null,
      setActiveProfileName: (activeProfileName) => set({ activeProfileName }),
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      rightPanelOpen: false,
      toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
      rightPanelTab: 'memory',
      setRightPanelTab: (rightPanelTab) => set({ rightPanelTab }),
    }),
    { name: 'agent-web-app' }
  )
)
