/**
 * React Router Configuration
 * Defines all application routes with lazy loading
 */

import React, { Suspense, lazy } from 'react'
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'

// Lazy load components for code splitting
const EmotionSphereTab = lazy(() => import('./EmotionSphereTab'))
const PsychologyPanel = lazy(() => import('./PsychologyPanel'))
const ExecutionPanel = lazy(() => import('./ExecutionPanel'))
const CrashDetectionPanel = lazy(() => import('./CrashDetectionPanel'))
const IgnitionPanel = lazy(() => import('./IgnitionPanel'))
const MicroMomentumPanel = lazy(() => import('./MicroMomentumPanel'))
const LoginScreen = lazy(() => import('./LoginScreen'))
const StoryCard = lazy(() => import('./StoryCard'))
const DecisionSupportPage = lazy(() => import('./DecisionSupportPage'))
const HabitsPage = lazy(() => import('./HabitsPage'))
const PersonaProfilePage = lazy(() => import('./PersonaProfilePage'))
const UserProfilePage = lazy(() => import('./UserProfilePage'))
const SettingsPage = lazy(() => import('./SettingsPage'))
const OnboardingPage = lazy(() => import('./OnboardingPage'))

// Loading fallback component
const PageLoader = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '100vh',
    flexDirection: 'column',
    gap: '16px'
  }}>
    <div className="loading-spinner" />
    <p>加载中...</p>
  </div>
)

// Auth guard wrapper (simplified - can be enhanced with actual auth logic)
const AuthLayout = () => {
  // Check if user is authenticated
  const isAuthenticated = localStorage.getItem('token') !== null
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <Outlet />
}

// Main layout with navigation
const MainLayout = () => (
  <Suspense fallback={<PageLoader />}>
    <Outlet />
  </Suspense>
)

// Route definitions
export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <EmotionSphereTab />
      },
      {
        path: 'psychology',
        element: <PsychologyPanel />
      },
      {
        path: 'execution',
        element: <ExecutionPanel />,
        children: [
          {
            path: 'crash-detection',
            element: <CrashDetectionPanel />
          },
          {
            path: 'ignition',
            element: <IgnitionPanel />
          },
          {
            path: 'momentum',
            element: <MicroMomentumPanel />
          }
        ]
      },
      {
        path: 'story/:storyId',
        element: <StoryCard />
      },
      {
        path: 'decision-support',
        element: <DecisionSupportPage />
      },
      {
        path: 'habits',
        element: <HabitsPage />
      },
      {
        path: 'persona',
        element: <PersonaProfilePage />
      },
      {
        path: 'login',
        element: <LoginScreen />
      },
      {
        path: 'onboarding',
        element: <OnboardingPage />
      },
      // Protected routes
      {
        element: <AuthLayout />,
        children: [
          {
            path: 'profile',
            element: <UserProfilePage />
          },
          {
            path: 'settings',
            element: <SettingsPage />
          }
        ]
      }
    ]
  },
  {
    path: '*',
    element: <div style={{ padding: 40, textAlign: 'center' }}>
      <h1>404 - 页面未找到</h1>
      <p>您访问的页面不存在</p>
    </div>
  }
])

// Navigation links configuration
export const NAV_LINKS = [
  { path: '/', label: '情绪星球', icon: '🌍' },
  { path: '/psychology', label: '心理分析', icon: '🧠' },
  { path: '/execution', label: '执行力', icon: '⚡' },
  { path: '/execution/crash-detection', label: '崩溃检测', icon: '🚨' },
  { path: '/execution/momentum', label: '动量追踪', icon: '📈' },
]
