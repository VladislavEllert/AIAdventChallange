import { useEffect } from 'react'
import { useAppStore } from '../stores/useAppStore'

export function useTheme() {
  const theme = useAppStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('theme-light', 'theme-dark')

    if (theme === 'light') {
      root.classList.add('theme-light')
    } else if (theme === 'dark') {
      root.classList.add('theme-dark')
    } else {
      const dark = window.matchMedia('(prefers-color-scheme: dark)').matches
      root.classList.add(dark ? 'theme-dark' : 'theme-light')
    }
  }, [theme])
}
