import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LuArrowUpRight } from 'react-icons/lu'
import HeroSection from '../components/HeroSection'
import HomeStory from '../components/HomeStory'
import HowItWorks from '../components/HowItWorks'
import ReportCarousel from '../components/reports/ReportCarousel'
import useReports from '../components/reports/useReports'
import Loading from '../components/Loading'

export default function Hero() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const { data, loading, error, retry } = useReports('page_size=3')
  const reports = data?.results || []

  function search(event) {
    event.preventDefault()
    const params = new URLSearchParams()
    if (query.trim()) params.set('q', query.trim())
    navigate(`/browse${params.size ? `?${params}` : ''}`)
  }

  return (
    <>
      <HeroSection query={query} onQueryChange={setQuery} onSearch={search} onReportLost={() => navigate('/report?type=lost')} onReportFound={() => navigate('/report?type=found')} />
      <HomeStory />
      <section aria-labelledby="recent-items-title" className="home-recent home-shell">
        <div className="home-recent-heading">
          <div><p className="home-eyebrow">THE CAMPUS BOARD</p><h2 id="recent-items-title">Recently reported items</h2><p>Check the latest public reports from your campus.</p></div>
          <Link to="/browse" className="home-text-link">Browse all items <LuArrowUpRight aria-hidden="true" /></Link>
        </div>
        {loading ? <Loading label="Loading recent reports…" /> : error ? (
          <div role="alert" className="home-board-empty"><div><strong>The campus board is taking a moment.</strong><p>{error}</p></div><button type="button" onClick={retry} className="home-text-link">Try again <LuArrowUpRight aria-hidden="true" /></button></div>
        ) : reports.length ? <ReportCarousel reports={reports} /> : (
          <div className="home-board-empty"><div><strong>No public reports yet.</strong><p>No public reports to show just yet. Lost or found something? Your report is a good place to start. New reports appear here after staff approval.</p></div><Link to="/report" className="home-text-link">Report an item <LuArrowUpRight aria-hidden="true" /></Link></div>
        )}
      </section>
      <HowItWorks />
    </>
  )
}

