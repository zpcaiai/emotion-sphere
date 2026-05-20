import { useState, useEffect, useCallback } from 'react'
import { getToken } from './auth'
import {
  fetchPersonaTags,
  fetchPersonaProfile,
  addPersonaTag,
  deletePersonaTag,
  extractPersonaTags,
} from './api'

const CATEGORY_COLORS = {
  emotion: '#ef4444',
  behavior: '#f59e0b',
  habit: '#22c55e',
  personality: '#3b82f6',
  cognition: '#8b5cf6',
  relationship: '#ec4899',
  value: '#06b6d4',
  manual: '#6366f1',
}

const CATEGORY_LABELS = {
  emotion: '情绪',
  behavior: '行为',
  habit: '习惯',
  personality: '性格',
  cognition: '认知',
  relationship: '关系',
  value: '价值观',
  manual: '手动',
  all: '全部',
}

function TagBadge({ tag, onDelete }) {
  const color = CATEGORY_COLORS[tag.tag_category] || '#6b7280'
  return (
    <span
      className="tag-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 10px',
        borderRadius: '16px',
        fontSize: '13px',
        fontWeight: 500,
        background: `${color}15`,
        color,
        border: `1px solid ${color}30`,
        cursor: onDelete ? 'pointer' : 'default',
      }}
      onClick={() => onDelete?.(tag)}
      title={`权重: ${tag.weight?.toFixed(1) || 1} | 频次: ${tag.frequency || 1} | 置信度: ${((tag.confidence || 0.8) * 100).toFixed(0)}%`}
    >
      {tag.tag_name}
      {tag.frequency > 1 && (
        <span style={{ fontSize: '10px', opacity: 0.7 }}>x{tag.frequency}</span>
      )}
    </span>
  )
}

function ScoreCard({ title, score, max = 10, color = '#3b82f6' }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100))
  let label = '一般'
  if (score >= 8) label = '优秀'
  else if (score >= 6) label = '良好'
  else if (score >= 4) label = '一般'
  else label = '需关注'

  return (
    <div className="score-card" style={{
      background: '#fff',
      borderRadius: '12px',
      padding: '16px',
      border: '1px solid #e5e7eb',
      minWidth: '140px',
    }}>
      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>{title}</div>
      <div style={{ fontSize: '28px', fontWeight: 700, color }}>{score.toFixed(1)}</div>
      <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>{label}</div>
      <div style={{
        width: '100%',
        height: '4px',
        background: '#e5e7eb',
        borderRadius: '2px',
        marginTop: '10px',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: color,
          borderRadius: '2px',
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}

function TrendBadge({ trend }) {
  const colors = {
    improving: '#22c55e',
    stable: '#3b82f6',
    declining: '#ef4444',
  }
  const labels = {
    improving: '上升',
    stable: '稳定',
    declining: '下降',
  }
  const color = colors[trend] || '#6b7280'
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      padding: '4px 10px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: 600,
      background: `${color}15`,
      color,
    }}>
      <span style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: color,
        display: 'inline-block',
      }} />
      {labels[trend] || trend}
    </span>
  )
}

function RiskBadge({ level }) {
  const colors = {
    low: '#22c55e',
    moderate: '#f59e0b',
    high: '#ef4444',
  }
  const labels = {
    low: '低风险',
    moderate: '中等风险',
    high: '高风险',
  }
  const color = colors[level] || '#6b7280'
  return (
    <span style={{
      padding: '4px 10px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: 600,
      background: `${color}15`,
      color,
    }}>
      {labels[level] || level}
    </span>
  )
}

export default function PersonaProfilePage() {
  const [profile, setProfile] = useState(null)
  const [tags, setTags] = useState([])
  const [activeCategory, setActiveCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [newTagCategory, setNewTagCategory] = useState('manual')
  const [extractText, setExtractText] = useState('')
  const [extractedTags, setExtractedTags] = useState([])
  const [extracting, setExtracting] = useState(false)

  const token = getToken()

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [profileData, tagsData] = await Promise.all([
        fetchPersonaProfile(token),
        fetchPersonaTags(token, activeCategory === 'all' ? null : activeCategory, 50),
      ])
      setProfile(profileData)
      setTags(tagsData.tags || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [token, activeCategory])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleAddTag = async () => {
    if (!newTagName.trim()) return
    try {
      await addPersonaTag(newTagName.trim(), newTagCategory, 2.0, token)
      setNewTagName('')
      setShowAddForm(false)
      loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteTag = async (tag) => {
    if (!confirm(`确定要删除标签 "${tag.tag_name}" 吗？`)) return
    try {
      await deletePersonaTag(tag.id, token)
      loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleExtract = async () => {
    if (!extractText.trim()) return
    setExtracting(true)
    try {
      const data = await extractPersonaTags(extractText, 'general', token)
      setExtractedTags(data.tags || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setExtracting(false)
    }
  }

  const categories = ['all', 'emotion', 'behavior', 'habit', 'personality', 'cognition', 'relationship']

  if (loading && !profile) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
        <div style={{ fontSize: '24px', marginBottom: '12px' }}></div>
        <div>加载人格画像中...</div>
      </div>
    )
  }

  return (
    <div className="persona-profile-page" style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 8px', color: '#1f2937' }}>
          我的人格画像
        </h1>
        <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>
          基于你的情绪记录、习惯养成和行为模式自动生成的唯一人格画像
        </p>
      </div>

      {error && (
        <div style={{
          background: '#fef2f2',
          color: '#ef4444',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '16px',
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}

      {/* 概览卡片 */}
      {profile && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '12px',
          marginBottom: '24px',
        }}>
          <ScoreCard title="情绪稳定性" score={profile.stability_score || 5} color="#3b82f6" />
          <ScoreCard title="心理韧性" score={profile.resilience_score || 5} color="#22c55e" />
          <div className="score-card" style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '16px',
            border: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: '8px',
          }}>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>成长趋势</div>
            <TrendBadge trend={profile.growth_trend || 'stable'} />
          </div>
          <div className="score-card" style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '16px',
            border: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: '8px',
          }}>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>风险等级</div>
            <RiskBadge level={profile.risk_level || 'low'} />
          </div>
        </div>
      )}

      {/* 标签实验区 */}
      <div style={{
        background: '#fff',
        borderRadius: '12px',
        padding: '16px',
        border: '1px solid #e5e7eb',
        marginBottom: '20px',
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 12px', color: '#1f2937' }}>
          从文本抽取标签
        </h3>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <input
            type="text"
            value={extractText}
            onChange={(e) => setExtractText(e.target.value)}
            placeholder="输入一段描述，自动抽取人格标签..."
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              fontSize: '14px',
              outline: 'none',
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
          />
          <button
            onClick={handleExtract}
            disabled={extracting || !extractText.trim()}
            style={{
              padding: '10px 18px',
              borderRadius: '8px',
              border: 'none',
              background: extracting ? '#9ca3af' : '#3b82f6',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 500,
              cursor: extracting ? 'not-allowed' : 'pointer',
            }}
          >
            {extracting ? '抽取中...' : '抽取'}
          </button>
        </div>
        {extractedTags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {extractedTags.map((tag, i) => (
              <TagBadge key={i} tag={tag} />
            ))}
          </div>
        )}
      </div>

      {/* 分类筛选 */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        marginBottom: '16px',
        alignItems: 'center',
      }}>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              border: 'none',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
              background: activeCategory === cat ? '#3b82f6' : '#f3f4f6',
              color: activeCategory === cat ? '#fff' : '#4b5563',
              transition: 'all 0.2s',
            }}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          style={{
            marginLeft: 'auto',
            padding: '6px 14px',
            borderRadius: '20px',
            border: '1px solid #3b82f6',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
            background: '#fff',
            color: '#3b82f6',
          }}
        >
          + 添加标签
        </button>
      </div>

      {/* 添加标签表单 */}
      {showAddForm && (
        <div style={{
          background: '#f8fafc',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '16px',
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
        }}>
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="标签名称"
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              fontSize: '14px',
            }}
          />
          <select
            value={newTagCategory}
            onChange={(e) => setNewTagCategory(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              fontSize: '14px',
              background: '#fff',
            }}
          >
            {categories.filter(c => c !== 'all').map((cat) => (
              <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
            ))}
          </select>
          <button
            onClick={handleAddTag}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: '#3b82f6',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            保存
          </button>
        </div>
      )}

      {/* 标签云 */}
      <div style={{
        background: '#fff',
        borderRadius: '12px',
        padding: '20px',
        border: '1px solid #e5e7eb',
        marginBottom: '20px',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0, color: '#1f2937' }}>
            我的标签
          </h3>
          <span style={{ fontSize: '13px', color: '#9ca3af' }}>
            共 {tags.length} 个标签
          </span>
        </div>

        {tags.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
            <div style={{ fontSize: '36px', marginBottom: '12px' }}></div>
            <div>还没有标签记录</div>
            <div style={{ fontSize: '13px', marginTop: '8px' }}>
              记录情绪、创建习惯或分析决策，系统将自动为你生成标签
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {tags.map((tag, i) => (
              <TagBadge key={`${tag.tag_name}-${i}`} tag={tag} onDelete={handleDeleteTag} />
            ))}
          </div>
        )}
      </div>

      {/* 维度分布 */}
      {profile && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
        }}>
          {[
            { key: 'emotion_dominance', label: '主导情绪', icon: '' },
            { key: 'behavior_patterns', label: '行为模式', icon: '' },
            { key: 'habit_strength', label: '习惯强度', icon: '' },
            { key: 'personality_vector', label: '性格特征', icon: '' },
          ].map((dim) => {
            const data = profile[dim.key] || {}
            const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 5)
            return (
              <div key={dim.key} style={{
                background: '#fff',
                borderRadius: '12px',
                padding: '16px',
                border: '1px solid #e5e7eb',
              }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 12px', color: '#374151' }}>
                  {dim.label}
                </h4>
                {entries.length === 0 ? (
                  <div style={{ color: '#9ca3af', fontSize: '13px' }}>暂无数据</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {entries.map(([name, score], i) => {
                      const maxScore = entries[0][1] || 1
                      const pct = (score / maxScore) * 100
                      return (
                        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '12px', color: '#6b7280', width: '20px' }}>{i + 1}</span>
                          <span style={{ fontSize: '13px', color: '#374151', minWidth: '70px' }}>{name}</span>
                          <div style={{ flex: 1, height: '6px', background: '#e5e7eb', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${pct}%`,
                              height: '100%',
                              background: CATEGORY_COLORS[dim.key === 'emotion_dominance' ? 'emotion' :
                                dim.key === 'behavior_patterns' ? 'behavior' :
                                  dim.key === 'habit_strength' ? 'habit' : 'personality'] || '#3b82f6',
                              borderRadius: '3px',
                            }} />
                          </div>
                          <span style={{ fontSize: '11px', color: '#9ca3af', width: '30px', textAlign: 'right' }}>
                            {score.toFixed(1)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* 画像说明 */}
      {profile?.note && (
        <div style={{
          marginTop: '20px',
          padding: '14px 16px',
          background: '#f0f9ff',
          borderRadius: '10px',
          border: '1px solid #bae6fd',
          fontSize: '13px',
          color: '#0369a1',
          lineHeight: 1.6,
        }}>
          {profile.note}
        </div>
      )}
    </div>
  )
}
