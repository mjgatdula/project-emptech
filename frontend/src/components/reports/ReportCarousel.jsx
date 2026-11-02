import { useEffect, useRef, useState } from 'react'
import { LuChevronLeft, LuChevronRight } from 'react-icons/lu'
import ReportCard from './ReportCard'

export default function ReportCarousel({ reports }) {
  const track = useRef(null)
  const [position, setPosition] = useState({ previous: false, next: false })

  function updatePosition() {
    const element = track.current
    if (!element) return
    const previous = element.scrollLeft > 2
    const next = element.scrollLeft + element.clientWidth < element.scrollWidth - 2
    setPosition((current) => current.previous === previous && current.next === next
      ? current
      : { previous, next })
  }

  useEffect(() => {
    const element = track.current
    if (!element) return
    const observer = new ResizeObserver(updatePosition)
    observer.observe(element)
    return () => observer.disconnect()
  }, [reports.length])

  function move(direction) {
    const element = track.current
    if (!element) return
    const card = element.firstElementChild
    const gap = parseFloat(getComputedStyle(element).columnGap) || 0
    const distance = card ? card.getBoundingClientRect().width + gap : element.clientWidth
    element.scrollBy({
      left: direction * distance,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
    })
  }

  function handleKeys(event) {
    if (event.target !== event.currentTarget) return
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      move(event.key === 'ArrowRight' ? 1 : -1)
    }
  }

  if (!reports.length) return <p className="mt-8 text-sm text-slate-600">No recent reports to display.</p>

  const hasOverflow = position.previous || position.next
  return (
    <div role="group" aria-roledescription="carousel" aria-label="Recent reports" className="mt-8">
      <div className="mb-4 flex items-center justify-between gap-4">
        <p id="recent-carousel-help" className="text-xs leading-6 text-slate-500">
          {hasOverflow ? 'Swipe, scroll, or use the arrows to browse.' : `Showing all ${reports.length} reports.`}
        </p>
        <div className="flex shrink-0 gap-2">
          <button type="button" aria-label="Previous reported item" aria-controls="recent-report-slides" disabled={!position.previous} onClick={() => move(-1)} className="grid h-11 w-11 place-items-center rounded-xl border border-slate-300 bg-white text-slate-900 transition hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-35">
            <LuChevronLeft aria-hidden="true" focusable="false" className="h-5 w-5" />
          </button>
          <button type="button" aria-label="Next reported item" aria-controls="recent-report-slides" disabled={!position.next} onClick={() => move(1)} className="grid h-11 w-11 place-items-center rounded-xl bg-brand-600 text-slate-900 transition hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-35">
            <LuChevronRight aria-hidden="true" focusable="false" className="h-5 w-5" />
          </button>
        </div>
      </div>
      <div id="recent-report-slides" ref={track} tabIndex={0} aria-label="Recent report slides" aria-describedby="recent-carousel-help" onScroll={updatePosition} onKeyDown={handleKeys} className="grid snap-x snap-mandatory auto-cols-[100%] grid-flow-col items-stretch gap-5 overflow-x-auto overscroll-x-contain rounded-2xl pb-4 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-500 sm:auto-cols-[calc((100%_-_1.25rem)/2)] lg:auto-cols-[calc((100%_-_2.5rem)/3)]">
        {reports.map((report, index) => (
          <div key={report.id} role="group" aria-roledescription="slide" aria-label={`${index + 1} of ${reports.length}: ${report.title}`} className="min-w-0 snap-start">
            <ReportCard report={report} />
          </div>
        ))}
      </div>
    </div>
  )
}
