import tippedLogo from '../../assets/tipped-hero.jpg'
import NotificationsLink from './NotificationsLink'
import Loading from '../Loading'
import { LuChevronDown, LuLogOut, LuMenu, LuUserRound, LuX } from 'react-icons/lu'
import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

// Account and role come from the verified authentication provider.
export default function Header({ user = null, onSignOut }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  async function handleSignOut() {
    if (!onSignOut || signingOut) return
    setSigningOut(true)
    try { await onSignOut() } finally { setSigningOut(false) }
  }
  const { pathname, search } = useLocation()
  // Keep the selected workflow visible while authentication redirects are pending.
  const nextPath = (new URLSearchParams(search).get('next') || '').split('?')[0]
  const reportInProgress = ['/login', '/register'].includes(pathname) && nextPath === '/report'
  const authLinkClass = ({ isActive }) => {
    const filled = !reportInProgress && isActive
    return `site-auth-link ${filled ? 'is-active' : ''}`
  }
  const closeMenu = () => setMenuOpen(false)
  const navClass = ({ isActive }) => `site-nav-link ${isActive ? 'is-active' : ''}`

  return (
    <header className={`tipped-site-header relative z-20 ${pathname === '/' ? 'tipped-home-header' : ''}`}>
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3 focus:text-brand-800">Skip to content</a>
      <div className="mx-auto flex min-h-[80px] max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4 lg:px-8">
        <Link to="/" onClick={closeMenu} aria-label="TIPPED home" className="flex shrink-0 items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-500">
          <img src={tippedLogo} alt="" width="796" height="247" className="site-brand-image" />
        </Link>
        <button type="button" aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)} className="rounded-lg border border-slate-600 px-3 py-2 text-sm font-semibold text-white focus-visible:outline-2 focus-visible:outline-brand-500 lg:hidden">{menuOpen ? <LuX aria-hidden="true" focusable="false" className="h-5 w-5" /> : <LuMenu aria-hidden="true" focusable="false" className="h-5 w-5" />}<span className="sr-only">{menuOpen ? 'Close menu' : 'Menu'}</span></button>
        <nav id="main-navigation" aria-label="Main navigation" className={`${menuOpen ? 'flex' : 'hidden'} w-full flex-col gap-4 border-t border-slate-700 pt-4 lg:flex lg:w-auto lg:flex-row lg:items-center lg:gap-5 lg:border-0 lg:pt-0`}>
          <div className="flex flex-col gap-1 lg:flex-row lg:items-center">
            <NavLink to="/" end className={navClass} onClick={closeMenu}>Home</NavLink>
            <NavLink to="/browse" className={navClass} onClick={closeMenu}>Browse Items</NavLink>
            <NavLink to="/report" className={({ isActive }) => navClass({ isActive: isActive || reportInProgress })} onClick={closeMenu}>Report an Item</NavLink>
            {user && <NavLink to="/my-reports" className={navClass} onClick={closeMenu}>My Reports</NavLink>}
          </div>
          {user ? (
            <div className="flex flex-wrap items-start gap-3">
              <NotificationsLink />
              <details className="relative">
                <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm font-semibold text-white"><LuUserRound aria-hidden="true" focusable="false" className="h-4 w-4" />Profile<LuChevronDown aria-hidden="true" focusable="false" className="h-4 w-4" /></summary>
                <div className="mt-2 grid w-40 gap-2 rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-lg lg:absolute lg:right-0">
                  <Link to="/profile" onClick={closeMenu} className="rounded p-2 text-slate-700 hover:bg-brand-50">My Profile</Link>
                  {user.isOsa && <Link to="/staff" onClick={closeMenu} className="rounded p-2 text-slate-700 hover:bg-brand-50">OSA Workspace</Link>}
                  {user.isAdmin && <Link to="/staff/settings" onClick={closeMenu} className="rounded p-2 text-slate-700 hover:bg-brand-50">Administration</Link>}
                  <button type="button" disabled={!onSignOut || signingOut} aria-busy={signingOut} onClick={handleSignOut} className="flex items-center gap-2 rounded p-2 text-left text-slate-700 hover:bg-brand-50 disabled:opacity-50">{signingOut ? <Loading inline label="Signing out..." /> : <><LuLogOut aria-hidden="true" focusable="false" className="h-4 w-4" />Sign Out</>}</button>
                </div>
              </details>
            </div>
          ) : (
            <div className="flex items-center gap-3 border-t border-slate-700 pt-4 lg:border-l lg:border-slate-700 lg:border-t-0 lg:pl-5 lg:pt-0">
              <NavLink to="/login" className={authLinkClass} onClick={closeMenu}>Sign In</NavLink>
              <NavLink to="/register" onClick={closeMenu} className={authLinkClass}>Register</NavLink>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}


