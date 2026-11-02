import useAuth from '../../context/useAuth'
import { useEffect, useState } from 'react'
import { apiRequest } from '../../data/api'

export default function useReports(query = '') {
  const { user } = useAuth()
  const identity = `${user?.id || 'guest'}:${Boolean(user?.isAdmin)}:${Boolean(user?.isOsa)}`
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState({ key: '', data: null, error: '' })
  const key = `${identity}:${query}:${revision}`
  useEffect(() => {
    const controller = new AbortController()
    apiRequest(`/reports/${query ? `?${query}` : ''}`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ key, data, error: '' }) })
      .catch((error) => { if (!controller.signal.aborted) setState({ key, data: null, error: error.message }) })
    return () => controller.abort()
  }, [query, key])
  const current = state.key === key
  return { data: current ? state.data : null, error: current ? state.error : '', loading: !current, retry: () => setRevision((value) => value + 1) }
}
