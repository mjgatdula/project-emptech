import { lazy, Suspense } from 'react'
import Loading from './components/Loading'
import Notifications from './pages/Notifications'
import { Route, Routes } from 'react-router-dom'
import SiteLayout from './components/layout/SiteLayout'
import PrivateRoute from './context/PrivateRoute'
import useAuth from './context/useAuth'
import Hero from './pages/Hero'
import Browse from './pages/Browse'
import ReportDetails from './pages/ReportDetails'
import Report from './pages/Report'
import MyReports from './pages/MyReports'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'
import NotFound from './pages/NotFound'

const Staff = lazy(() => import('./pages/Staff'))
const Administration = lazy(() => import('./pages/Administration'))

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route element={<SiteLayout user={user} />}>
        <Route index element={<Hero />} />
        <Route path="browse" element={<Browse />} />
        <Route path="browse/:id" element={<ReportDetails />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="report" element={<Report key={user?.id || 'guest'} user={user} />} />
        <Route path="my-reports" element={<PrivateRoute><MyReports key={user?.id || 'guest'} /></PrivateRoute>} />
        <Route path="notifications" element={<PrivateRoute><Notifications key={user?.id || 'guest'} /></PrivateRoute>} />
        <Route path="staff" element={<PrivateRoute osaOnly><Suspense fallback={<Loading />}><Staff key={user?.id || 'guest'} /></Suspense></PrivateRoute>} />
        <Route path="staff/settings" element={<PrivateRoute adminOnly><Suspense fallback={<Loading />}><Administration key={user?.id || 'guest'} /></Suspense></PrivateRoute>} />
        <Route path="profile" element={<PrivateRoute><Profile key={user?.id || 'guest'} /></PrivateRoute>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
