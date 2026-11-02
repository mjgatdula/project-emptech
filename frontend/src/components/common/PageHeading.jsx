export default function PageHeading({ title, children, eyebrow = 'TIPPED / CAMPUS LOST & FOUND' }) {
  return <div className="page-heading"><p className="app-eyebrow">{eyebrow}</p><h1>{title}</h1>{children && <p className="page-description">{children}</p>}</div>
}
