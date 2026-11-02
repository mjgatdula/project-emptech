import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 px-6 py-8 text-sm sm:flex-row lg:px-8">
        <div><Link to="/" className="font-bold text-slate-900">TIPPED · Campus Lost &amp; Found</Link><p className="mt-2 text-slate-500">Helping belongings find their way back.</p>
          <details className="mt-3 text-xs text-slate-500">
            <summary className="w-fit cursor-pointer underline underline-offset-4">Image credits</summary>
            <p className="mt-2 max-w-md leading-6">Campus photograph: <a href="https://commons.wikimedia.org/wiki/File:Technological_Institute_of_the_Philippines_Manila.jpg" target="_blank" rel="noreferrer" className="underline underline-offset-4">JamBreboneria / Wikimedia Commons</a>, <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer" className="underline underline-offset-4">CC BY-SA 4.0</a>. Cropped for display.</p>
          </details>
        </div>
        <div className="max-w-sm text-xs leading-6 text-slate-500">T.I.P. campus lost and found · Confirm item ownership and pickup arrangements with authorized staff.</div>
      </div>
    </footer>
  )
}
