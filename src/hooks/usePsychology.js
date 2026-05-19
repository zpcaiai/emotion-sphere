/**
 * React Query hooks for Psychology Engine API
 * Provides caching, background refetching, and optimistic updates
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api'

// Query keys for cache management
const QUERY_KEYS = {
  psychology: {
    analyze: (text) => ['psychology', 'analyze', text?.slice(0, 50)],
    dashboard: () => ['psychology', 'dashboard'],
    history: (limit = 20) => ['psychology', 'history', limit],
  },
  identity: {
    narrative: () => ['identity', 'narrative'],
    reinforcements: () => ['identity', 'reinforcements'],
    migrations: () => ['identity', 'migrations'],
  },
  execution: {
    momentum: () => ['execution', 'momentum'],
    sessions: () => ['execution', 'sessions'],
  },
  habits: {
    list: () => ['habits', 'list'],
    regulation: () => ['habits', 'regulation'],
  },
}

// Psychology Analysis
export function useEmotionAnalysis() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ text, intensity, context }) => 
      api.analyzeEmotion(text, intensity, context),
    onSuccess: (data) => {
      // Invalidate related queries to refresh data
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.psychology.dashboard() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.psychology.history() })
      
      // Optimistically update cache
      queryClient.setQueryData(
        QUERY_KEYS.psychology.analyze(data.input_text),
        data
      )
    },
    onError: (error) => {
      console.error('Emotion analysis failed:', error)
    }
  })
}

export function usePsychologyDashboard() {
  return useQuery({
    queryKey: QUERY_KEYS.psychology.dashboard(),
    queryFn: () => api.getPsychologyDashboard(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
  })
}

export function useAnalysisHistory(limit = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.psychology.history(limit),
    queryFn: () => api.getAnalysisHistory(limit),
    staleTime: 2 * 60 * 1000,
  })
}

// Identity & Narrative
export function useIdentityReinforcement() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload) => api.reinforceIdentity(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.identity.reinforcements() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.identity.migrations() })
    }
  })
}

export function useIdentityMigrations() {
  return useQuery({
    queryKey: QUERY_KEYS.identity.migrations(),
    queryFn: () => api.getPersonalityMigrations(),
    staleTime: 10 * 60 * 1000,
  })
}

export function useCurrentNarrative() {
  return useQuery({
    queryKey: QUERY_KEYS.identity.narrative(),
    queryFn: () => api.getCurrentNarrative(),
    staleTime: 5 * 60 * 1000,
  })
}

// Execution & Micro-Momentum
export function useMicroMomentum() {
  return useQuery({
    queryKey: QUERY_KEYS.execution.momentum(),
    queryFn: () => api.getMicroMomentum(),
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  })
}

export function useCompleteSession() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload) => api.completeSession(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.execution.momentum() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.execution.sessions() })
    }
  })
}

// Habits & Behavior Regulation
export function useBehaviorRegulation() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload) => api.regulateBehavior(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.regulation() })
    }
  })
}

export function useHabitList() {
  return useQuery({
    queryKey: QUERY_KEYS.habits.list(),
    queryFn: () => api.getHabits(),
    staleTime: 5 * 60 * 1000,
  })
}

// Utility hooks for prefetching
export function usePrefetchPsychology() {
  const queryClient = useQueryClient()
  
  return {
    prefetchDashboard: () => 
      queryClient.prefetchQuery({
        queryKey: QUERY_KEYS.psychology.dashboard(),
        queryFn: () => api.getPsychologyDashboard(),
      }),
    prefetchMomentum: () =>
      queryClient.prefetchQuery({
        queryKey: QUERY_KEYS.execution.momentum(),
        queryFn: () => api.getMicroMomentum(),
      })
  }
}
