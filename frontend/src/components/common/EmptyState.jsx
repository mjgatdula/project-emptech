import { LuArrowDownLeft } from 'react-icons/lu'
export default function EmptyState({ title, description, children }) {
  return <div className="empty-state"><span className="empty-state-mark" aria-hidden="true"><LuArrowDownLeft /></span><h2>{title}</h2>{description && <p>{description}</p>}{children && <div className="empty-state-actions">{children}</div>}</div>
}
