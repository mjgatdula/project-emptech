import { Link } from 'react-router-dom'
import { LuArrowUpRight, LuClipboardCheck } from 'react-icons/lu'

export default function HomeStory() {
  return (
    <section className="home-belonging home-shell" aria-labelledby="belonging-title">
      <div className="home-care-icon" aria-hidden="true"><LuClipboardCheck /></div>
      <div className="home-belonging-copy">
        <p className="home-eyebrow">FOUND SOMETHING ON CAMPUS?</p>
        <h2 id="belonging-title">Be someone’s next good news.</h2>
        <p>Report what you found and bring it to OSA. Authorized staff review the report, record physical receipt, and check ownership before returning it.</p>
      </div>
      <Link className="btn-secondary" to="/report?type=found">Report a found item <LuArrowUpRight aria-hidden="true" /></Link>
    </section>
  )
}
