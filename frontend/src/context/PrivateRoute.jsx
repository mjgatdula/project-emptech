import { Navigate, Outlet, useLocation } from 'react-router-dom'
import useAuth from './useAuth'
import Loading from '../components/Loading'

export default function PrivateRoute({ children, osaOnly = false, adminOnly = false }) {
  const { user, isAuthenticated, isLoading, backendConnected, authError, refreshSession } = useAuth()
  const location = useLocation()

  if (isLoading) return <Loading label="Checking your session..." />

  if (!backendConnected) {
    return (
      <div role="alert" className="mx-auto max-w-xl px-6 py-12">
        <h1 className="text-xl font-semibold text-slate-900">Unable to verify your session</h1>
        <p className="mt-3 text-sm text-slate-600">{authError || 'Please try connecting again.'}</p>
        <button type="button" onClick={refreshSession} className="mt-5 rounded-xl bg-brand-600 px-5 py-3 font-semibold text-slate-900">
          Try again
        </button>
      </div>
    )
  }

  if (!isAuthenticated) {
    const next = location.pathname + location.search
    return (
      <Navigate
        to={`/login?${new URLSearchParams({ next })}`}
        state={{ from: location }}
        replace
      />
    )
  }

  if ((osaOnly && !user.isOsa) || (adminOnly && !user.isAdmin)) return <Navigate to="/profile" replace />

  return children ?? <Outlet />
}
