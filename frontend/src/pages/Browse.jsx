import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { LuSearch, LuSlidersHorizontal, LuX, LuArrowUpRight } from 'react-icons/lu'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import EmptyState from '../components/common/EmptyState'
import Pagination from '../components/common/Pagination'
import ReportCard from '../components/reports/ReportCard'
import useReports from '../components/reports/useReports'
import Loading from '../components/Loading'
import useApi from '../data/useApi'

export default function Browse() {
  const [params, setParams] = useSearchParams()
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [validation, setValidation] = useState('')
  const catalogue = useApi('/catalogue/')
  const { data, loading, error, retry } = useReports(params.toString())
  const active = ['type', 'site', 'category', 'from', 'to'].filter(key => params.get(key))
  function search(event) {
    event.preventDefault()
    const next = new URLSearchParams()
    for (const [key, value] of new FormData(event.currentTarget)) if (String(value).trim()) next.set(key, String(value).trim())
    if (!catalogue.data) {
      for (const key of ['site', 'category']) if (params.get(key)) next.set(key, params.get(key))
    }
    if (next.get('from') && next.get('to') && next.get('from') > next.get('to')) { setValidation('Choose an end date on or after the start date.'); setFiltersOpen(true); return }
    setValidation(''); setParams(next)
  }
  function selectType(type) {
    const next = new URLSearchParams(params)
    if (type) next.set('type', type); else next.delete('type')
    next.delete('page'); setValidation(''); setParams(next)
  }
  function remove(key) { const next = new URLSearchParams(params); next.delete(key); next.delete('page'); setParams(next) }
  function page(value) { const next = new URLSearchParams(params); next.set('page', value); setParams(next) }
  function filterName(key) {
    const value = params.get(key)
    if (key === 'site' || key === 'category') return (catalogue.data?.[key === 'site' ? 'sites' : 'categories'] || []).find(row => String(row.id) === value)?.name || `${key}: ${value}`
    return key === 'type' ? `${value === 'found' ? 'Found' : 'Lost'} items` : `${key === 'from' ? 'From' : 'Until'} ${value}`
  }
  const hasSearch = active.length > 0 || Boolean(params.get('q'))
  return <section className="app-page browse-page">
    <div className="page-title-row"><PageHeading title="Find your next lead." eyebrow="THE CAMPUS BOARD">Search lost and found reports by item, campus, category or incident date.</PageHeading><Link className="btn-primary" to="/report">Report an item <LuArrowUpRight aria-hidden="true" /></Link></div>
    <form key={`${Boolean(catalogue.data)}:${JSON.stringify(['q', 'site', 'category', 'from', 'to'].map(key => params.get(key) || ''))}`} onSubmit={search} className="browse-search-form" role="search" aria-label="Search item reports">
      <label htmlFor="browse-query" className="label">What are you looking for?</label>
      <div className="browse-search-line"><LuSearch aria-hidden="true" /><input id="browse-query" name="q" type="search" defaultValue={params.get('q') || ''} placeholder="Item, location or reference number" maxLength={255} /><button className="btn-primary" type="submit">Search</button></div>
      <div className="browse-filter-toolbar"><fieldset className="browse-types"><legend className="sr-only">Show reports</legend>{[['', 'All items'], ['found', 'Found items'], ['lost', 'Lost items']].map(([value, label]) => <label key={value}><input type="radio" name="type" value={value} checked={(params.get('type') || '') === value} onChange={() => selectType(value)} /><span>{label}</span></label>)}</fieldset><button type="button" className="btn-secondary browse-filter-toggle" aria-expanded={filtersOpen} aria-controls="browse-filter-fields" onClick={() => setFiltersOpen(!filtersOpen)}><LuSlidersHorizontal aria-hidden="true" />Filters{active.length ? ` (${active.length})` : ''}</button></div>
      <div id="browse-filter-fields" className={`browse-filter-fields ${filtersOpen ? 'is-open' : ''}`}>
        {[['site', 'Campus', 'sites'], ['category', 'Category', 'categories']].map(([key, label, collection]) => <label className="label" key={key}>{label}<select className="field" name={key} defaultValue={params.get(key) || ''} disabled={catalogue.loading}><option value="">{catalogue.loading ? 'Loading options…' : `All ${label === 'Campus' ? 'campuses' : 'categories'}`}</option>{(catalogue.data?.[collection] || []).map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>)}
        <details className="date-refinement" open={Boolean(params.get('from') || params.get('to')) || undefined}><summary>Incident date range <span>Optional</span></summary><div className="date-fields"><label className="label">From<input className="field" type="date" name="from" defaultValue={params.get('from') || ''} /></label><label className="label">To<input className="field" type="date" name="to" defaultValue={params.get('to') || ''} /></label></div></details>
        <button className="btn-secondary browse-apply" type="submit">Apply filters</button>
      </div><Feedback error={validation} />
    </form>
    {catalogue.error && <div className="resource-error"><Feedback error={`Filter options are unavailable. ${catalogue.error}`} /><button type="button" className="btn-secondary" onClick={catalogue.retry}>Retry filter options</button></div>}
    {hasSearch && <div className="active-refinements" aria-label="Applied search and filters">{params.get('q') && <button type="button" onClick={() => remove('q')}>“{params.get('q')}” <LuX aria-label="Remove search" /></button>}{active.map(key => <button key={key} type="button" onClick={() => remove(key)}>{filterName(key)} <LuX aria-label={`Remove ${key} filter`} /></button>)}<button type="button" className="clear-refinements" onClick={() => { setParams({}); setValidation('') }}>Clear all</button></div>}
    <div className="results-heading"><p role="status" aria-live="polite">{loading ? 'Looking through the campus board…' : error ? 'The board is temporarily unavailable' : <><strong>{data?.count || 0}</strong> {(data?.count || 0) === 1 ? 'report' : 'reports'}{hasSearch ? ' matching your search' : ' on the board'}</>}</p><span>Newest first</span></div>
    {loading ? <Loading label="Loading reports…" /> : error ? <EmptyState title="Let’s try that again." description={error}><button className="btn-primary" onClick={retry}>Retry loading reports</button></EmptyState> : data?.results?.length ? <div className="report-grid">{data.results.map(report => <ReportCard key={report.id} report={report} />)}</div> : <EmptyState title={hasSearch ? 'No match just yet.' : 'No public reports yet.'} description={hasSearch ? 'Try a broader description or remove a filter. You can also report what you lost so campus staff can help.' : 'No approved public reports are available yet. Your own pending reports are kept in My Reports.'}>{hasSearch && <button className="btn-secondary" onClick={() => setParams({})}>Clear search & filters</button>}<Link className="btn-primary" to="/report">Report an item</Link></EmptyState>}
    <Pagination data={data} onPage={page} />
  </section>
}

