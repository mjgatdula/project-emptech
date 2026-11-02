import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LuBell } from 'react-icons/lu'
import useApi from '../../data/useApi'

export default function NotificationsLink() {
  const { pathname } = useLocation()
  const { data, retry } = useApi(`/notifications/?view=${encodeURIComponent(pathname)}`)
  useEffect(() => {
    const refresh = () => { if (!document.hidden) retry() }
    window.addEventListener('tipped:notifications', refresh)
    const timer = setInterval(refresh, 60000)
    return () => { clearInterval(timer); window.removeEventListener('tipped:notifications', refresh) }
  }, [retry])
  return <Link to="/notifications" className="notification-nav"><LuBell aria-hidden="true" />Notifications{Boolean(data?.unread) && <span className="rounded-full bg-brand-600 px-2 py-0.5 text-xs text-slate-900">{data.unread}</span>}</Link>
}
