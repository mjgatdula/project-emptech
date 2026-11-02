import { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Header from './Header'
import Footer from './Footer'
import useAuth from '../../context/useAuth'

export default function SiteLayout({ user }) {
  const { pathname } = useLocation()
  const { signOut, authError, loading, refreshSession } = useAuth()
  const main = useRef(null)
  const previousPath = useRef(pathname)

  useEffect(() => {
    const pageName = pathname === '/' ? 'Campus Lost & Found' : pathname.startsWith('/browse') ? 'Browse Items' : pathname === '/report' ? 'Report an Item' : pathname === '/login' ? 'Sign In' : pathname === '/register' ? 'Register' : pathname === '/my-reports' ? 'My Reports & Claims' : pathname === '/profile' ? 'My Profile' : pathname === '/notifications' ? 'Notifications' : pathname === '/staff/settings' ? 'Campus Administration' : pathname === '/staff' ? 'OSA Workspace' : 'Page not found'
    document.title = `TIPPED · ${pageName}`
    if (previousPath.current !== pathname) {
      window.scrollTo(0, 0)
      main.current?.focus({ preventScroll: true })
      previousPath.current = pathname
    }
  }, [pathname])

  return <div className={`tipped-product flex min-h-screen flex-col ${pathname === '/' ? 'is-home' : 'is-workspace'}`}><Header key={pathname} user={user} onSignOut={signOut} /><main id="main-content" ref={main} tabIndex={-1} className="app-main outline-none"><>{authError && !loading && <div role="alert" className="mx-auto my-4 max-w-7xl rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">{authError}<button type="button" onClick={refreshSession} className="ml-4 font-semibold underline">Retry connection</button></div>}<Outlet /></></main><Footer /></div>
}
