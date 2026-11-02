import { useEffect, useState } from 'react'
import useAuth from '../../context/useAuth'
import { apiRequest } from '../../data/api'
import ItemIcon from '../common/ItemIcon'

export default function ReportPhoto({ path, title = 'Reported item', className = 'h-44 w-full object-contain' }) {
  const { user } = useAuth()
  const identity = `${user?.id || 'guest'}:${Boolean(user?.isOsa)}`
  const key = `${identity}:${path || ''}`
  const [state, setState] = useState({ key: '', url: '' })
  useEffect(() => {
    if (!path) return undefined
    const controller = new AbortController()
    let url = ''
    apiRequest(path, { signal: controller.signal, responseType: 'blob' }).then((blob) => {
      if (controller.signal.aborted) return
      url = URL.createObjectURL(blob)
      setState({ key, url })
    }).catch(() => { /* A missing/private image keeps the neutral placeholder. */ })
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url) }
  }, [path, key])
  return path && state.key === key && state.url
    ? <img src={state.url} alt={title} className={className} />
    : <span className={`grid place-items-center rounded-xl bg-slate-50 ${className.includes('h-12') ? 'h-12 w-12' : 'min-h-28'}`}><ItemIcon className="h-10 w-10" /><span className="sr-only">No available photograph</span></span>
}
