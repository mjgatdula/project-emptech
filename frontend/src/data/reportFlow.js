export const reportSteps = [
  { title: 'Sign In', detail: 'Your campus account' },
  { title: 'Report Type', detail: 'Lost or found' },
  { title: 'Item Details', detail: 'Describe the item' },
  { title: 'Place & Time', detail: 'Where and when' },
  { title: 'Review & Submit', detail: 'Check your report' },
  { title: 'Track Report', detail: 'Follow staff updates' },
]

export const reportCategories = ['Electronics', 'ID / Cards', 'Personal belongings', 'School supplies', 'Other']

export function createReportDraft(type) {
  return { type: ['lost', 'found'].includes(type) ? type : '', title: '', category: '', description: '', site: '', location: '', date: localToday(), time: '', unknownTime: true, validity: '30' }
}

export function localToday() {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function validateReportStep(step, draft) {
  if (step === 1 && !['lost', 'found'].includes(draft.type)) return 'Choose whether this is a lost or found item.'
  if (step === 2) {
    if (draft.title.trim().length < 3) return 'Enter an item title with at least 3 characters.'
    if (!draft.category) return 'Choose an item category.'
    if (draft.description.trim().length < 10) return 'Describe the item in at least 10 characters.'
  }
  if (step === 3) {
    if (!draft.site) return 'Choose a campus.'
    if (draft.location.trim().length < 3) return 'Enter a specific location with at least 3 characters.'
    if (!draft.date || draft.date > localToday()) return 'Choose the date lost or found, on or before today.'
    if (!draft.unknownTime && !draft.time) return 'Enter an approximate time or select Time unknown.'
  }
  return ''
}


export function reportPayload(draft, photo) {
  const data = new FormData()
  for (const [key, value] of Object.entries({ report_type: draft.type, title: draft.title.trim(), category: draft.category,
    description: draft.description.trim(), site: draft.site, location: draft.location.trim(), item_date: draft.date,
    time: draft.unknownTime ? '' : draft.time })) data.set(key, value)
  if (draft.validity) data.set('validity_days', draft.validity)
  if (photo?.file) data.set('image', photo.file)
  if (draft.removeImage) data.set('remove_image', 'true')
  return data
}

export function draftFromReport(report) {
  return { type: report.report_type, title: report.title, category: String(report.category), description: report.description,
    site: String(report.site), location: report.location, date: report.date, time: report.time?.slice(0, 5) || '',
    unknownTime: !report.time, validity: '', isEdit: true, removeImage: false }
}
