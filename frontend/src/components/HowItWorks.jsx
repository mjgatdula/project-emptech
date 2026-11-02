import { LuClipboardCheck, LuClipboardPen, LuHandshake, LuSearch } from 'react-icons/lu'

const steps = [
  {
    icon: LuSearch,
    title: 'Search',
    description: 'Check lost and found reports first. Someone may already have reported your missing belonging.',
    actor: 'Students and campus users',
  },
  {
    icon: LuClipboardPen,
    title: 'Report',
    description: 'Describe what you lost or found. Keep contact details and private ownership clues out of the public description.',
    actor: 'Students and finders',
  },
  {
    icon: LuClipboardCheck,
    title: 'Review & Receive',
    description: 'Authorized staff review the listing and separately record physical receipt of a found item. Approval does not mean the item is in custody.',
    actor: 'OSA / authorized staff',
  },
  {
    icon: LuHandshake,
    title: 'Verify & Return',
    description: 'Staff check private ownership evidence before recording a confirmed physical handover to the owner.',
    actor: 'Owner and authorized staff',
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="steps-title" className="border-t border-slate-100 bg-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <p className="text-xs font-bold tracking-[0.18em] text-brand-800">HOW TIPPED WORKS</p>
        <h2 id="steps-title" className="mt-3 text-3xl font-bold tracking-tight text-slate-900">A clear path back to its owner.</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">The TIPPED workflow keeps listing review, physical custody, and ownership checks separate.</p>
        <ol className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(({ icon: Icon, title, description, actor }, index) => (
            <li key={title} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between gap-3">
                <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-600 text-slate-900"><Icon aria-hidden="true" focusable="false" className="h-6 w-6" /></span>
                <span aria-hidden="true" className="text-sm font-bold text-slate-500">0{index + 1}</span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-slate-900">{title}</h3>
              <p className="mb-5 mt-3 text-sm leading-7 text-slate-600">{description}</p>
              <p className="mt-auto border-t border-slate-100 pt-4 text-xs font-semibold leading-6 text-brand-800"><span className="sr-only">Handled by: </span>{actor}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
