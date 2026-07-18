<!-- source: agent-web/frontend/src/App.tsx | title: App.tsx -->

import { useTheme } from './hooks/useTheme'
import MainLayout from './components/layout/MainLayout'

export default function App() {
  useTheme()
  return <MainLayout />
}
