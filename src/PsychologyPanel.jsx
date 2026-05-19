import { useState, useEffect } from 'react'
import { analyzePsychology, fetchPsychologyDashboard, fetchBehavioralExperiments, completeBehavioralExperiment } from './api'
import { getToken } from './auth'
import './PsychologyPanel.css'

// 情绪强度滑块组件
function IntensitySlider({ value, onChange }) {
  const labels = ['1-平静', '2', '3', '4', '5-中等', '6', '7', '8', '9', '10-极度强烈']
  return (
    <div className="intensity-slider">
      <label>情绪强度: <strong>{value}</strong> - {labels[value - 1]}</label>
      <input
        type="range"
        min="1"
        max="10"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="intensity-range"
      />
      <div className="intensity-labels">
        <span>平静</span>
        <span>强烈</span>
      </div>
    </div>
  )
}

// L0: 人格因果分析展示
function L0CausalPanel({ driver }) {
  if (!driver) return null

  const cycle = driver.behavioral_cycle || {}

  return (
    <div className="layer-panel l0-panel">
      <h3 className="layer-title">
        <span className="layer-badge">L0</span>
        人格因果引擎 (WHY)
      </h3>

      <div className="causal-chain">
        <div className="chain-item">
          <span className="chain-label">表层问题</span>
          <p>{driver.surface_problem || '待分析'}</p>
        </div>
        <div className="chain-arrow">↓</div>
        <div className="chain-item highlight">
          <span className="chain-label">深层情绪</span>
          <p>{driver.deep_emotion || '待分析'}</p>
        </div>
        <div className="chain-arrow">↓</div>
        <div className="chain-item danger">
          <span className="chain-label">隐藏心理动力</span>
          <p>{driver.hidden_dynamics || '待分析'}</p>
        </div>
      </div>

      {cycle.trigger && (
        <div className="behavioral-cycle">
          <h4>行为循环</h4>
          <div className="cycle-flow">
            <span className="cycle-node trigger">{cycle.trigger}</span>
            <span className="cycle-arrow">→</span>
            <span className="cycle-node emotion">{cycle.emotion}</span>
            <span className="cycle-arrow">→</span>
            <span className="cycle-node escape">{cycle.escape}</span>
            <span className="cycle-arrow">→</span>
            <span className="cycle-node shame">{cycle.shame}</span>
            <span className="cycle-arrow">↺</span>
          </div>
        </div>
      )}

      <div className="driver-meta">
        <div className="meta-item">
          <label>类型</label>
          <span className={`tag type-${(driver.driver_category || '').toLowerCase()}`}>
            {driver.driver_category || '未知'}
          </span>
        </div>
        <div className="meta-item">
          <label>核心信念</label>
          <blockquote>{driver.core_belief || '待探索'}</blockquote>
        </div>
        <div className="meta-item">
          <label>长期风险</label>
          <p className="risk-warning">{driver.long_term_risk || '暂无评估'}</p>
        </div>
      </div>
    </div>
  )
}

// L1: 认知图式与行为实验
function L1RegulationPanel({ schema, experiment }) {
  if (!schema && !experiment) return null

  return (
    <div className="layer-panel l1-panel">
      <h3 className="layer-title">
        <span className="layer-badge">L1</span>
        行为调节引擎 (HOW)
      </h3>

      {schema && (
        <div className="schema-section">
          <h4>认知图式分析 (REBT ABC模型)</h4>
          <div className="abc-model">
            <div className="abc-item">
              <span className="abc-letter">A</span>
              <span className="abc-label">诱发事件</span>
              <p>{schema.activating_event || (schema.abc_analysis && schema.abc_analysis.activating_event) || '待分析'}</p>
            </div>
            <div className="abc-item">
              <span className="abc-letter">B</span>
              <span className="abc-label">信念系统</span>
              <p className="irrational-belief">{schema.core_belief || '待分析'}</p>
              <span className="distortion-tag">{schema.distortion_type}</span>
            </div>
            <div className="abc-item">
              <span className="abc-letter">C</span>
              <span className="abc-label">情绪/行为结果</span>
              <p>{schema.consequence_emotional || (schema.abc_analysis && schema.abc_analysis.consequence_emotional)}</p>
              <p className="behavioral-result">{schema.consequence_behavioral || (schema.abc_analysis && schema.abc_analysis.consequence_behavioral)}</p>
            </div>
          </div>

          {schema.cognitive_reframing_patch && (
            <div className="reframing-box">
              <h5>认知重构补丁</h5>
              <blockquote className="reframing-quote">
                "{schema.cognitive_reframing_patch}"
              </blockquote>
            </div>
          )}
        </div>
      )}

      {experiment && (
        <div className="experiment-section">
          <h4>行为实验 (CBT)</h4>
          <div className="experiment-card">
            <div className="experiment-header">
              <span className="exp-id">{experiment.experiment_id}</span>
              <span className="exp-difficulty">难度: {experiment.difficulty_level}/5</span>
            </div>
            <h5>{experiment.title}</h5>
            <div className="experiment-content">
              <div className="exp-hypothesis">
                <label>待证伪假设:</label>
                <p>{experiment.hypothesis_to_test}</p>
              </div>
              <div className="exp-action">
                <label>行动指令:</label>
                <p className="action-text">{experiment.counter_behavioral_action}</p>
                <span className="duration">⏱ {experiment.estimated_duration_minutes}分钟</span>
              </div>
              <div className="exp-metric">
                <label>遥测指标:</label>
                <code>{experiment.binary_telemetry_metric}</code>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// L2: 状态机与执行力引导
function L2ExecutionPanel({ state }) {
  if (!state) return null

  const stateColors = {
    'CRISIS': '#ff4444',
    'DYSREGULATED': '#ff8800',
    'REGULATED': '#ffcc00',
    'FLOW': '#44ff44',
    'INTEGRATED': '#4444ff'
  }

  return (
    <div className="layer-panel l2-panel">
      <h3 className="layer-title">
        <span className="layer-badge">L2</span>
        执行力边缘引导 (NOW)
      </h3>

      <div className="state-display" style={{ borderColor: stateColors[state.state_name] || '#ccc' }}>
        <div className="state-header">
          <span className="state-name" style={{ color: stateColors[state.state_name] }}>
            {state.state_name}
          </span>
          <span className="state-level">Level {state.state_level}/4</span>
        </div>

        <div className="state-dimensions">
          <div className="dimension">
            <label>生理唤醒</label>
            <div className="dim-bar">
              <div className="dim-fill" style={{ width: `${state.arousal_level * 10}%` }}></div>
            </div>
            <span>{state.arousal_level}/10</span>
          </div>
          <div className="dimension">
            <label>情绪效价</label>
            <div className="dim-bar valence">
              <div className="dim-fill" style={{
                width: `${Math.abs(state.valence_score) * 10}%`,
                marginLeft: state.valence_score < 0 ? 'auto' : 0,
                marginRight: state.valence_score > 0 ? 'auto' : 0,
                background: state.valence_score > 0 ? '#44ff44' : '#ff4444'
              }}></div>
            </div>
            <span>{state.valence_score > 0 ? '+' : ''}{state.valence_score}</span>
          </div>
          <div className="dimension">
            <label>专注能力</label>
            <div className="dim-bar">
              <div className="dim-fill" style={{ width: `${state.focus_capacity * 10}%` }}></div>
            </div>
            <span>{state.focus_capacity}/10</span>
          </div>
        </div>
      </div>

      <div className="intervention-box">
        <h4>即时干预建议</h4>
        <p className="recommended-action">{state.recommended_action}</p>
        {state.escalation_protocol && (
          <div className="escalation-protocol">
            <label>升级协议:</label>
            <p>{state.escalation_protocol}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// L3: 身份认同
function L3IdentityPanel({ identity }) {
  if (!identity) return (
    <div className="layer-panel l3-panel placeholder">
      <h3 className="layer-title">
        <span className="layer-badge">L3</span>
        身份认同系统 (WHO AM I)
      </h3>
      <p className="placeholder-text">记录更多情绪日志后，将生成您的身份认同分析...</p>
    </div>
  )

  return (
    <div className="layer-panel l3-panel">
      <h3 className="layer-title">
        <span className="layer-badge">L3</span>
        身份认同系统 (WHO AM I)
      </h3>

      <div className="narrative-card">
        <span className="narrative-type">{identity.narrative_type}</span>
        <h4>{identity.narrative_title}</h4>

        <div className="identity-themes">
          {identity.identity_themes && identity.identity_themes.map((theme, i) => (
            <span key={i} className="theme-tag">{theme}</span>
          ))}
        </div>

        <div className="core-values">
          <h5>核心价值</h5>
          {identity.core_values && identity.core_values.map((cv, i) => (
            <div key={i} className="value-item">
              <span className="value-name">{cv.value}</span>
              <div className="value-bar">
                <div className="value-fill" style={{ width: `${cv.importance * 10}%` }}></div>
              </div>
            </div>
          ))}
        </div>

        <div className="narrative-timeline">
          <h5>人生转折点</h5>
          {identity.turning_points && identity.turning_points.map((tp, i) => (
            <div key={i} className="timeline-item">
              <span className="timeline-age">{tp.age}岁</span>
              <p>{tp.event_description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// L4: 成长轨迹
function L4GrowthPanel({ growth }) {
  if (!growth) return (
    <div className="layer-panel l4-panel placeholder">
      <h3 className="layer-title">
        <span className="layer-badge">L4</span>
        长期记忆与成长 (LONG-TERM)
      </h3>
      <p className="placeholder-text">持续记录情绪和行为，将生成您的成长轨迹...</p>
    </div>
  )

  return (
    <div className="layer-panel l4-panel">
      <h3 className="layer-title">
        <span className="layer-badge">L4</span>
        长期记忆与成长 (LONG-TERM)
      </h3>

      <div className="growth-metrics">
        <div className="metric-row">
          <div className="metric-card">
            <label>情绪调节能力</label>
            <div className="metric-value">{growth.emotion_regulation_capacity}/10</div>
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${growth.emotion_regulation_capacity * 10}%` }}></div>
            </div>
          </div>
          <div className="metric-card">
            <label>行为灵活性</label>
            <div className="metric-value">{growth.behavioral_flexibility}/10</div>
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${growth.behavioral_flexibility * 10}%` }}></div>
            </div>
          </div>
        </div>

        <div className="metric-row">
          <div className="metric-card">
            <label>认知重构频率</label>
            <div className="metric-value">{growth.cognitive_reframing_frequency}/10</div>
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${growth.cognitive_reframing_frequency * 10}%` }}></div>
            </div>
          </div>
          <div className="metric-card">
            <label>自我觉察深度</label>
            <div className="metric-value">{growth.self_awareness_depth}/10</div>
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${growth.self_awareness_depth * 10}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      <div className="patterns-section">
        <h4>模式识别</h4>
        <div className="patterns-list">
          {growth.recurring_patterns && growth.recurring_patterns.map((pattern, i) => (
            <div key={i} className="pattern-item">
              <span className="pattern-name">{pattern.pattern_name}</span>
              <span className={`pattern-type ${pattern.pattern_type}`}>{pattern.pattern_type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// 行为实验追踪组件
function ExperimentTracker({ experiments, onComplete }) {
  const [selectedExperiment, setSelectedExperiment] = useState(null)
  const [outcome, setOutcome] = useState('')
  const [reflection, setReflection] = useState('')

  if (!experiments || experiments.length === 0) {
    return (
      <div className="experiment-tracker empty">
        <p>暂无进行中的行为实验</p>
      </div>
    )
  }

  const handleSubmit = (expId) => {
    onComplete(expId, { completed: true, notes: outcome }, reflection)
    setSelectedExperiment(null)
    setOutcome('')
    setReflection('')
  }

  return (
    <div className="experiment-tracker">
      <h4>进行中的行为实验</h4>
      <div className="experiment-list">
        {experiments.map((exp) => (
          <div key={exp.experiment_id} className="experiment-row">
            <div className="exp-info">
              <span className="exp-title">{exp.title}</span>
              <span className="exp-status">{exp.status}</span>
            </div>
            {selectedExperiment === exp.experiment_id ? (
              <div className="exp-complete-form">
                <input
                  type="text"
                  placeholder="实验结果..."
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                />
                <textarea
                  placeholder="反思..."
                  value={reflection}
                  onChange={(e) => setReflection(e.target.value)}
                />
                <button onClick={() => handleSubmit(exp.experiment_id)}>提交</button>
                <button onClick={() => setSelectedExperiment(null)}>取消</button>
              </div>
            ) : (
              <button onClick={() => setSelectedExperiment(exp.experiment_id)}>
                完成
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// 主组件
export default function PsychologyPanel() {
  const [inputText, setInputText] = useState('')
  const [intensity, setIntensity] = useState(5)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [experiments, setExperiments] = useState([])

  const token = getToken()

  // 加载仪表盘数据
  useEffect(() => {
    loadDashboard()
    loadExperiments()
  }, [token])

  const loadDashboard = async () => {
    try {
      const data = await fetchPsychologyDashboard(token)
      setDashboard(data)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    }
  }

  const loadExperiments = async () => {
    try {
      const data = await fetchBehavioralExperiments('active', 10, token)
      setExperiments(data.items || [])
    } catch (err) {
      console.error('Failed to load experiments:', err)
    }
  }

  const handleAnalyze = async () => {
    if (!inputText.trim()) return

    setLoading(true)
    setError(null)

    try {
      const result = await analyzePsychology(inputText, intensity, true, token)
      setAnalysis(result)
      // 刷新仪表盘和实验列表
      loadDashboard()
      loadExperiments()
    } catch (err) {
      setError(err.message || '分析失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCompleteExperiment = async (expId, outcome, reflection) => {
    try {
      await completeBehavioralExperiment(expId, outcome, reflection, token)
      loadExperiments()
      loadDashboard()
    } catch (err) {
      console.error('Failed to complete experiment:', err)
    }
  }

  // 提取各层数据
  const l0Data = analysis?.layers?.L0_causal?.personality_driver
  const l1Data = analysis?.layers?.L1_regulation
  const l2Data = analysis?.layers?.L2_execution?.psychological_state
  const l3Data = analysis?.layers?.L3_identity?.identity_narrative
  const l4Data = analysis?.layers?.L4_memory?.growth_metrics

  return (
    <div className="psychology-panel">
      <div className="psychology-header">
        <h2>🧠 心理学分析</h2>
        <p>L0-L4 多层心理架构分析</p>
      </div>

      {/* 输入区域 */}
      <div className="input-section">
        <div className="section-title">情绪输入</div>
        <textarea
          className="emotion-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="描述你当前的情绪、处境或困扰..."
          rows={4}
        />
        <IntensitySlider value={intensity} onChange={setIntensity} />
        <button
          className="analyze-btn"
          onClick={handleAnalyze}
          disabled={loading || !inputText.trim()}
        >
          {loading ? '分析中...' : '开始分析'}
        </button>
        {error && <div className="error-message">{error}</div>}
      </div>

      {/* 仪表盘概览 */}
      {dashboard && (
        <div className="dashboard-summary">
          <div className="stat-row">
            <div className="stat-item">
              <span className="stat-value">{dashboard.total_logs || 0}</span>
              <span className="stat-label">情绪记录</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{dashboard.total_schemas || 0}</span>
              <span className="stat-label">认知图式</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{dashboard.active_experiments || 0}</span>
              <span className="stat-label">行为实验</span>
            </div>
          </div>
        </div>
      )}

      {/* 分析结果 - L0-L4 层级展示 */}
      {analysis && (
        <div className="analysis-results">
          <div className="section-title">多层分析结果</div>

          <div className="layers-container">
            <L0CausalPanel driver={l0Data} />
            <L1RegulationPanel schema={l1Data?.cognitive_schema} experiment={l1Data?.behavioral_experiment} />
            <L2ExecutionPanel state={l2Data} />
            <L3IdentityPanel identity={l3Data} />
            <L4GrowthPanel growth={l4Data} />
          </div>
        </div>
      )}

      {/* 行为实验追踪 */}
      <div className="experiments-section">
        <div className="section-title">行为实验追踪</div>
        <ExperimentTracker
          experiments={experiments}
          onComplete={handleCompleteExperiment}
        />
      </div>
    </div>
  )
}
