import { Link } from 'react-router-dom'
import EmptyState from '../components/common/EmptyState'
export default function NotFound() {
  return <section className="app-page app-page-narrow"><h1 className="app-eyebrow mb-6">404 / PAGE NOT FOUND</h1><EmptyState title="A different way back." description="This page may have moved or the link may be incomplete. The campus board is a good place to start again."><Link to="/browse" className="btn-primary">Browse items</Link><Link to="/" className="btn-secondary">Return home</Link></EmptyState></section>
}
