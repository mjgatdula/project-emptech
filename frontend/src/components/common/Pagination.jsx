import { LuArrowLeft, LuArrowRight } from 'react-icons/lu'
export default function Pagination({ data, onPage }) {
  if (!data || data.pages <= 1) return null
  return <nav aria-label="Results pages" className="app-pagination"><button type="button" className="btn-secondary" disabled={!data.hasPrevious} onClick={() => onPage(data.page - 1)}><LuArrowLeft aria-hidden="true" />Previous</button><span aria-live="polite">Page <strong>{data.page}</strong> of {data.pages}</span><button type="button" className="btn-secondary" disabled={!data.hasNext} onClick={() => onPage(data.page + 1)}>Next<LuArrowRight aria-hidden="true" /></button></nav>
}
