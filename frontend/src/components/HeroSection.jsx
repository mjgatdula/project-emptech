import { Link } from 'react-router-dom'
import { LuArrowUpRight, LuSearch, LuShieldCheck } from 'react-icons/lu'
import campusImage from '../assets/hero.jpg'
import './HeroSection.css'

export default function HeroSection({ query, onQueryChange, onSearch, onReportLost, onReportFound }) {
  return (
    <section id="home" className="home-experience" aria-labelledby="home-title">
      <div className="home-shell home-opening">
        <div className="home-opening-grid">
          <div className="home-introduction">
            <p className="home-eyebrow">T.I.P. CAMPUS LOST &amp; FOUND</p>
            <h1 id="home-title" className="home-title">Lost it?<br /><span>Let’s find it.</span></h1>
            <p className="home-intro-note">Your campus. Your belongings. One place to search for a missing item or help someone get theirs back.</p>
            <div className="home-actions">
              <button type="button" onClick={onReportLost} className="home-action home-action-primary">I lost something <LuArrowUpRight aria-hidden="true" /></button>
              <button type="button" onClick={onReportFound} className="home-action home-action-secondary">I found something <LuArrowUpRight aria-hidden="true" /></button>
            </div>
            <form role="search" onSubmit={onSearch} className="home-search">
              <label htmlFor="hero-search" className="sr-only">Search reported items</label>
              <LuSearch aria-hidden="true" />
              <input id="hero-search" type="search" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Search items, locations or details" />
              <button type="submit">Search <LuArrowUpRight aria-hidden="true" /></button>
            </form>
            <Link to="/browse" className="home-browse-link">Browse all lost &amp; found items <LuArrowUpRight aria-hidden="true" /></Link>
          </div>
          <div id="campus-story" className="home-campus-panel">
            <figure className="home-campus-frame">
              <img className="home-campus-image" src={campusImage} alt="The Technological Institute of the Philippines Manila campus, with its familiar yellow sign" width="1600" height="898" fetchPriority="high" decoding="async" />
              <figcaption className="home-campus-caption"><span>CONNECTED BY CAMPUS.</span><strong>A familiar place.<br /> A helping hand.</strong></figcaption>
            </figure>
            <div className="home-trust-note"><LuShieldCheck aria-hidden="true" /><p><strong>Thoughtful returns, guided by staff.</strong><span>Ownership checks and physical handover are handled separately.</span></p></div>
            <a className="home-photo-credit" href="https://commons.wikimedia.org/wiki/File:Technological_Institute_of_the_Philippines_Manila.jpg" target="_blank" rel="noreferrer">Photo: JamBreboneria / Wikimedia · CC BY-SA 4.0 · cropped</a>
          </div>
        </div>
      </div>
    </section>
  )
}



