import { useState, useCallback } from 'react'
import { generateIgnitionSequence, reportTelemetry } from './api'
import { getToken } from './auth'

export default function IgnitionPanel({ crashState, onSequenceComplete }) {
  const [sequence, setSequence] = useState(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [completedSteps, setCompletedSteps] = useState(new Set())
  const [sessionActive, setSessionActive] = useState(false)
  const [sessionStartTime, setSessionStartTime] = useState(null)

  const generateSequence = useCallback(async () => {
    setLoading(true)
    try {
      const token = getToken()
      const result = await generateIgnitionSequence(crashState?.core_resistance || '拖延', crashState?.risk_score || 0.5, token)
      setSequence(result)
      setCurrentStep(0)
      setCompletedSteps(new Set())
    } catch (err) { console.error('Failed to generate sequence:', err) }
    finally { setLoading(false) }
  }, [crashState])

  const startStep = (idx) => { setCurrentStep(idx); setSessionActive(true); setSessionStartTime(Date.now()) }

  const completeStep = async (success) => {
    if (!sequence) return
    const step = sequence.steps[currentStep]
    const durationMinutes = sessionStartTime ? Math.round((Date.now() - sessionStartTime) / 60000) : 0
    try { await reportTelemetry('execution_edge', { session_id: sequence.session_id, step_id: step.step_id, completed: success, duration_minutes: durationMinutes, user_state_at_completion: success ? 'REGULATED' : 'DYSREGULATED' }, getToken()) }
    catch (err) { console.error('Telemetry report failed:', err) }
    if (success) setCompletedSteps(prev => new Set([...prev, currentStep]))
    setSessionActive(false); setSessionStartTime(null)
    if (currentStep >= sequence.steps.length - 1 && onSequenceComplete) {
      onSequenceComplete({ session_id: sequence.session_id, completed_steps: completedSteps.size + (success ? 1 : 0), total_steps: sequence.steps.length })
    }
  }

  const getIcon = (type) => ({ 'GROUNDING': '🧘', 'MICRO_ACTION': '⚡', 'TWO_MINUTE_START': '▶️', 'BODY_CHECK': '💪', 'REWARD': '🎉' }[type] || '•')

  if (!sequence) {
    return (
      <div className="exec-panel ignition-panel">
        <h3 className="panel-title"><span className="panel-icon">🔥</span>点火序列</h3>
        <div className="ignition-intro">
          <p>2分钟点火协议帮助您从崩溃边缘恢复执行力</p>
          <button className="generate-btn" onClick={generateSequence} disabled={loading}>{loading ? '生成中...' : '生成点火序列'}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="exec-panel ignition-panel">
      <h3 className="panel-title"><span className="panel-icon">🔥</span>点火序列<span className="session-id">#{sequence.session_id?.slice(0, 8)}</span></h3>
      <div className="sequence-progress">
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${(completedSteps.size / sequence.steps.length) * 100}%` }} /></div>
        <span className="progress-text">{completedSteps.size} / {sequence.steps.length} 完成</span>
      </div>
      <div className="steps-list">
        {sequence.steps.map((step, idx) => {
          const isCompleted = completedSteps.has(idx)
          const isCurrent = currentStep === idx && sessionActive
          const isPending = idx > currentStep || (!sessionActive && idx === currentStep && !isCompleted)
          return (
            <div key={step.step_id} className={`step-item ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''} ${isPending ? 'pending' : ''}`}>
              <div className="step-header">
                <span className="step-icon">{getIcon(step.step_type)}</span>
                <span className="step-number">{idx + 1}</span>
                <span className="step-title">{step.title}</span>
                <span className="step-duration">{step.duration_seconds}s</span>
              </div>
              {!isCompleted && (
                <div className="step-actions">
                  {sessionActive && isCurrent ? (
                    <>
                      <p className="step-instruction">{step.instruction}</p>
                      <div className="step-controls">
                        <button className="success-btn" onClick={() => completeStep(true)}>✓ 完成</button>
                        <button className="fail-btn" onClick={() => completeStep(false)}>✗ 跳过</button>
                      </div>
                    </>
                  ) : isPending ? (
                    <button className="start-btn" onClick={() => startStep(idx)} disabled={sessionActive}>开始</button>
                  ) : null}
                </div>
              )}
              {isCompleted && <div className="step-completed-badge">✓ 已完成</div>}
            </div>
          )
        })}
      </div>
      {completedSteps.size === sequence.steps.length && (
        <div className="sequence-complete">
          <span className="complete-icon">🎉</span>
          <p>点火序列完成！执行力已恢复</p>
          <button className="new-sequence-btn" onClick={() => setSequence(null)}>开始新的序列</button>
        </div>
      )}
    </div>
  )
}
