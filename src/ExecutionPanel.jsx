import { useState } from 'react'
import CrashDetectionPanel from './CrashDetectionPanel'
import IgnitionPanel from './IgnitionPanel'
import MicroMomentumPanel from './MicroMomentumPanel'
import './ExecutionPanel.css'

export default function ExecutionPanel() {
  const [crashState, setCrashState] = useState(null)
  const [activeTab, setActiveTab] = useState('crash')
  const [showIgnition, setShowIgnition] = useState(false)

  const handleCrashDetected = (state) => {
    setCrashState(state)
    if (state.detected) {
      setShowIgnition(true)
      setActiveTab('ignition')
    }
  }

  const handleSequenceComplete = () => {
    setActiveTab('momentum')
  }

  return (
    <div className="execution-container">
      <div className="execution-header">
        <h2>⚡ 执行力干预系统</h2>
        <p>崩溃检测 · 点火序列 · 微动量追踪</p>
      </div>

      <div className="execution-tabs">
        <button 
          className={`exec-tab ${activeTab === 'crash' ? 'active' : ''}`}
          onClick={() => setActiveTab('crash')}
        >
          ⚠️ 崩溃检测
        </button>
        <button 
          className={`exec-tab ${activeTab === 'ignition' ? 'active' : ''}`}
          onClick={() => setActiveTab('ignition')}
          disabled={!showIgnition}
        >
          🔥 点火序列
        </button>
        <button 
          className={`exec-tab ${activeTab === 'momentum' ? 'active' : ''}`}
          onClick={() => setActiveTab('momentum')}
        >
          📈 微动量
        </button>
      </div>

      {activeTab === 'crash' && (
        <CrashDetectionPanel 
          onCrashDetected={handleCrashDetected}
          onStateChange={setCrashState}
        />
      )}

      {activeTab === 'ignition' && (
        <IgnitionPanel 
          crashState={crashState}
          onSequenceComplete={handleSequenceComplete}
        />
      )}

      {activeTab === 'momentum' && <MicroMomentumPanel />}
    </div>
  )
}
