import { LuCircleAlert, LuCircleCheck } from 'react-icons/lu'
export default function Feedback({ error, message }) {
  if (!error && !message) return null
  const Icon = error ? LuCircleAlert : LuCircleCheck
  return <div role={error ? 'alert' : 'status'} className={`app-feedback ${error ? 'is-error' : 'is-success'}`}><Icon aria-hidden="true" /><p>{error || message}</p></div>
}
