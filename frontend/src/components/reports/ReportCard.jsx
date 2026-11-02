import ReportPhoto from './ReportPhoto'
import { LuArrowUpRight, LuMapPin } from 'react-icons/lu'
import { Link } from 'react-router-dom'
export default function ReportCard({ report }) {
  const found = report.report_type === 'found'
  return <article className="report-card"><Link className="report-card-media" to={`/browse/${report.id}`} tabIndex={-1} aria-hidden="true"><ReportPhoto path={report.image} title={report.title} className="report-card-photo" /><span className={`report-type ${found ? 'type-found' : 'type-lost'}`}>{found ? 'Found item' : 'Lost item'}</span></Link><div className="report-card-content"><p className="report-card-category">{report.categoryName || 'Campus belonging'} <span>{report.date}</span></p><h3><Link to={`/browse/${report.id}`}>{report.title}<LuArrowUpRight aria-hidden="true" /></Link></h3><p className="report-card-location"><LuMapPin aria-hidden="true" />{report.siteName}{report.siteName && report.location ? ' · ' : ''}{report.location}</p><p className="report-card-reference">{report.reference}</p></div></article>
}
