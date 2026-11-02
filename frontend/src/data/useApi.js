import useAuth from '../context/useAuth'
import { useCallback, useEffect, useState } from 'react'
import { apiRequest } from './api'

export default function useApi(path) {
  const { user } = useAuth()
  const identity = `${user?.id || 'guest'}:${Boolean(user?.isAdmin)}:${Boolean(user?.isOsa)}`
  const [revision, setRevision] = useState(0)
  const key = `${identity}:${path}:${revision}`
  const [state, setState] = useState({ key: '', data: null, error: '' })
  useEffect(() => {
    if (!path) return undefined
    const controller = new AbortController()
    apiRequest(path, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ key, data, error: '' }) })
      .catch((error) => { if (!controller.signal.aborted) setState({ key, data: null, error: error.message }) })
    return () => controller.abort()
  }, [path, key])
  const retry = useCallback(() => setRevision(value => value + 1), [])
  const current = key === state.key
  return { data: current ? state.data : null, loading: Boolean(path && !current), error: current ? state.error : '', retry }
}
