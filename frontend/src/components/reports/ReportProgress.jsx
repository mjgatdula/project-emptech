import { LuCheck } from 'react-icons/lu'
import { reportSteps } from '../../data/reportFlow'
export default function ReportProgress({ currentStep = 0, completed = [], preview = false, onStepChange }) {
  return <nav aria-label="Reporting progress" className="report-progress"><p className="report-progress-summary" aria-live="polite"><span>Step {Math.min(currentStep + 1, reportSteps.length)} of {reportSteps.length}</span><strong>{reportSteps[currentStep].title}</strong>{preview && <span>Preview · sign in to submit</span>}</p><ol>{reportSteps.map((step, index) => {
    const done = completed.includes(index), current = index === currentStep
    const available = Boolean(onStepChange && index < currentStep && index !== 5)
    return <li key={step.title} className={`${current ? 'is-current' : ''} ${done ? 'is-done' : ''}`} aria-current={current ? 'step' : undefined}><button type="button" disabled={!available} onClick={() => onStepChange(index)} aria-label={`${step.title}${current ? ', current step' : done ? ', completed' : ', upcoming'}`}><span className="step-marker" aria-hidden="true">{done ? <LuCheck /> : String(index + 1).padStart(2, '0')}</span><span>{step.title}</span></button></li>
  })}</ol></nav>
}
