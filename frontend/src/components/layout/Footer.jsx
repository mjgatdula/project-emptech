import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 px-6 py-8 text-sm sm:flex-row lg:px-8">
        <div><Link to="/" className="font-bold text-slate-900">TIPPED · Campus Lost &amp; Found</Link><p className="mt-2 text-slate-500">Helping belongings find their way back.</p></div>
        <div className="max-w-sm text-xs leading-6 text-slate-500">T.I.P. campus lost and found · Confirm item ownership and pickup arrangements with authorized staff.</div>
      </div>
    </footer>
  )
}
