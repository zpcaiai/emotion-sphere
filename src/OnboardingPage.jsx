import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getToken, getCachedUser, setCachedUser } from './auth'
import { API_BASE } from './api'

// ── DiceBear 头像生成 ────────────────────────────────────────
const AVATAR_STYLES = [
  { id: 'lorelei',      label: '精灵系', emoji: '🧝' },
  { id: 'adventurer',   label: '冒险家', emoji: '⚔️' },
  { id: 'avataaars',    label: '卡通人', emoji: '😊' },
  { id: 'big-smile',    label: '大笑脸', emoji: '😄' },
  { id: 'croodles',     label: '涂鸦风', emoji: '✏️' },
  { id: 'fun-emoji',    label: '表情包', emoji: '🤪' },
  { id: 'micah',        label: '极简线', emoji: '🎨' },
  { id: 'personas',     label: '写实风', emoji: '👤' },
]
const AVATAR_SEEDS = ['alpha','bravo','charlie','delta','echo','foxtrot','gamma','hotel',
                      'india','juliet','kilo','lima','mike','nova','oscar','papa']

function avatarUrl(style, seed) {
  return `https://api.dicebear.com/9.x/${style}/svg?seed=${seed}&size=80&radius=50`
}

// ── MBTI 快测题目 ────────────────────────────────────────────
const MBTI_QUESTIONS = [
  { id: 'EI', q: '在聚会中，你通常会...', a: ['主动认识陌生人，越热闹越好', '观察周围，等对方先来搭话'], labels: ['E', 'I'] },
  { id: 'EI', q: '一个人独处时，你会感到...', a: ['有点无聊，想找人说话', '放松充电，享受宁静'], labels: ['E', 'I'] },
  { id: 'SN', q: '学习新事物时，你更喜欢...', a: ['具体步骤和实际案例', '理解背后的原理和可能性'], labels: ['S', 'N'] },
  { id: 'SN', q: '描述一次旅行，你更注重...', a: ['具体的景点、美食、行程', '整体的感受和内心体验'], labels: ['S', 'N'] },
  { id: 'TF', q: '帮朋友做决定时，你更倾向...', a: ['分析利弊，给出逻辑建议', '先共情感受，再陪他想办法'], labels: ['T', 'F'] },
  { id: 'TF', q: '发生争执后，你更在意...', a: ['谁的逻辑更合理', '对方的情绪是否受到了伤害'], labels: ['T', 'F'] },
  { id: 'JP', q: '计划出行，你会...', a: ['提前订好全部行程和住宿', '大方向定了，细节随缘走'], labels: ['J', 'P'] },
  { id: 'JP', q: '面对截止日期，你通常...', a: ['早早完成，不让任务压着', '临近截止才爆发效率'], labels: ['J', 'P'] },
]

function computeMBTI(answers) {
  const score = { E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 }
  MBTI_QUESTIONS.forEach((q, i) => {
    const choice = answers[i]
    if (choice === 0) score[q.labels[0]]++
    else if (choice === 1) score[q.labels[1]]++
  })
  const type =
    (score.E >= score.I ? 'E' : 'I') +
    (score.S >= score.N ? 'S' : 'N') +
    (score.T >= score.F ? 'T' : 'F') +
    (score.J >= score.P ? 'J' : 'P')
  const vector = { E: score.E, I: score.I, S: score.S, N: score.N, T: score.T, F: score.F, J: score.J, P: score.P }
  return { type, vector }
}

// ── 情感观选项 ────────────────────────────────────────────────
const EMOTION_STYLES = [
  { id: 'expressive',  label: '表达型',  desc: '喜欢直接说出感受，情绪流动自然', icon: '💬' },
  { id: 'reflective',  label: '内省型',  desc: '习惯独自消化，深思后再分享',     icon: '🌙' },
  { id: 'empathetic',  label: '共情型',  desc: '对他人情绪敏感，善于感同身受',   icon: '🤝' },
  { id: 'analytical',  label: '分析型',  desc: '倾向用理性框架理解和处理情绪',   icon: '🔍' },
  { id: 'creative',    label: '创造型',  desc: '用艺术、写作等方式表达情感',     icon: '🎨' },
  { id: 'action',      label: '行动型',  desc: '通过运动或做事来消化情绪',       icon: '⚡' },
]

// ── 兴趣标签 ─────────────────────────────────────────────────
const INTEREST_OPTIONS = [
  { id: 'music',     label: '音乐',   icon: '🎵' },
  { id: 'reading',   label: '阅读',   icon: '📚' },
  { id: 'sports',    label: '运动',   icon: '🏃' },
  { id: 'travel',    label: '旅行',   icon: '✈️' },
  { id: 'art',       label: '艺术',   icon: '🎨' },
  { id: 'cooking',   label: '烹饪',   icon: '🍳' },
  { id: 'gaming',    label: '游戏',   icon: '🎮' },
  { id: 'film',      label: '影视',   icon: '🎬' },
  { id: 'tech',      label: '科技',   icon: '💻' },
  { id: 'nature',    label: '自然',   icon: '🌿' },
  { id: 'fitness',   label: '健身',   icon: '💪' },
  { id: 'photo',     label: '摄影',   icon: '📷' },
  { id: 'writing',   label: '写作',   icon: '✍️' },
  { id: 'pets',      label: '宠物',   icon: '🐾' },
  { id: 'coffee',    label: '咖啡',   icon: '☕' },
  { id: 'fashion',   label: '穿搭',   icon: '👗' },
]

const TOTAL_STEPS = 4  // MBTI → 情感观 → 兴趣 → 头像

// ── 样式常量 ─────────────────────────────────────────────────
const s = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '24px 16px 48px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
    color: '#fff',
  },
  header: {
    width: '100%',
    maxWidth: '600px',
    marginBottom: '28px',
  },
  progress: {
    display: 'flex',
    gap: '6px',
    marginBottom: '12px',
  },
  progressDot: (active, done) => ({
    flex: 1,
    height: '4px',
    borderRadius: '2px',
    background: done ? '#7c6aff' : active ? '#a78bfa' : 'rgba(255,255,255,0.15)',
    transition: 'background 0.3s',
  }),
  card: {
    width: '100%',
    maxWidth: '600px',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '20px',
    padding: '28px 24px',
    backdropFilter: 'blur(20px)',
  },
  title: { fontSize: '22px', fontWeight: 700, marginBottom: '6px' },
  subtitle: { fontSize: '14px', color: 'rgba(255,255,255,0.55)', marginBottom: '24px' },
  question: { fontSize: '17px', fontWeight: 600, marginBottom: '14px', lineHeight: 1.5 },
  choiceRow: { display: 'flex', flexDirection: 'column', gap: '10px' },
  choiceBtn: (selected) => ({
    padding: '14px 16px',
    borderRadius: '12px',
    border: selected ? '1.5px solid #7c6aff' : '1px solid rgba(255,255,255,0.1)',
    background: selected ? 'rgba(124,106,255,0.2)' : 'rgba(255,255,255,0.04)',
    color: '#fff',
    fontSize: '15px',
    textAlign: 'left',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  }),
  tagGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
    gap: '10px',
  },
  tag: (selected) => ({
    padding: '10px 8px',
    borderRadius: '12px',
    border: selected ? '1.5px solid #7c6aff' : '1px solid rgba(255,255,255,0.1)',
    background: selected ? 'rgba(124,106,255,0.2)' : 'rgba(255,255,255,0.04)',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    textAlign: 'center',
    transition: 'all 0.2s',
  }),
  navRow: {
    display: 'flex',
    gap: '12px',
    marginTop: '28px',
  },
  backBtn: {
    flex: 1,
    padding: '14px',
    borderRadius: '12px',
    border: '1px solid rgba(255,255,255,0.2)',
    background: 'transparent',
    color: '#fff',
    fontSize: '16px',
    cursor: 'pointer',
  },
  nextBtn: (disabled) => ({
    flex: 2,
    padding: '14px',
    borderRadius: '12px',
    border: 'none',
    background: disabled ? 'rgba(124,106,255,0.3)' : 'linear-gradient(135deg,#7c6aff,#a78bfa)',
    color: disabled ? 'rgba(255,255,255,0.4)' : '#fff',
    fontSize: '16px',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s',
  }),
  styleGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
  },
  styleCard: (selected) => ({
    padding: '14px 12px',
    borderRadius: '14px',
    border: selected ? '1.5px solid #7c6aff' : '1px solid rgba(255,255,255,0.1)',
    background: selected ? 'rgba(124,106,255,0.2)' : 'rgba(255,255,255,0.04)',
    color: '#fff',
    cursor: 'pointer',
    transition: 'all 0.2s',
    textAlign: 'left',
  }),
  avatarStyleRow: {
    display: 'flex',
    gap: '8px',
    overflowX: 'auto',
    paddingBottom: '8px',
    marginBottom: '16px',
  },
  avatarStyleChip: (selected) => ({
    padding: '6px 12px',
    borderRadius: '20px',
    border: selected ? '1.5px solid #7c6aff' : '1px solid rgba(255,255,255,0.15)',
    background: selected ? 'rgba(124,106,255,0.25)' : 'rgba(255,255,255,0.06)',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    flexShrink: 0,
  }),
  avatarGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '12px',
  },
  avatarItem: (selected) => ({
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
    padding: '8px',
    borderRadius: '14px',
    border: selected ? '2px solid #7c6aff' : '1.5px solid transparent',
    background: selected ? 'rgba(124,106,255,0.2)' : 'rgba(255,255,255,0.04)',
    cursor: 'pointer',
    transition: 'all 0.2s',
  }),
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)          // 0=MBTI 1=情感 2=兴趣 3=头像
  const [mbtiAnswers, setMbtiAnswers] = useState({})  // questionIndex -> 0|1
  const [mbtiQ, setMbtiQ] = useState(0)               // current MBTI question
  const [emotionStyle, setEmotionStyle] = useState('')
  const [interests, setInterests] = useState([])
  const [avatarStyle, setAvatarStyle] = useState('lorelei')
  const [avatarSeed, setAvatarSeed] = useState('alpha')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // 已完成则跳过
  useEffect(() => {
    const token = getToken()
    if (!token) { navigate('/login', { replace: true }); return }
    fetch(`${API_BASE}/profile/survey`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { if (d.completed) navigate('/', { replace: true }) })
      .catch(() => {})
  }, [])

  const toggleInterest = useCallback((id) => {
    setInterests(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 8 ? [...prev, id] : prev
    )
  }, [])

  const mbtiDone = mbtiQ >= MBTI_QUESTIONS.length
  const canNextMBTI = mbtiQ < MBTI_QUESTIONS.length
    ? mbtiAnswers[mbtiQ] !== undefined
    : true

  const handleMBTIChoice = (choice) => {
    setMbtiAnswers(prev => ({ ...prev, [mbtiQ]: choice }))
    setTimeout(() => {
      if (mbtiQ < MBTI_QUESTIONS.length - 1) setMbtiQ(q => q + 1)
      else setMbtiQ(MBTI_QUESTIONS.length)  // 完成
    }, 220)
  }

  const handleSubmit = async () => {
    setSaving(true); setError('')
    const { type, vector } = computeMBTI(mbtiAnswers)
    try {
      const token = getToken()
      const res = await fetch(`${API_BASE}/profile/survey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          mbti_type: type,
          mbti_vector: vector,
          emotion_style: emotionStyle,
          interest_tags: interests,
          avatar_id: avatarSeed,
          avatar_style: avatarStyle,
          extra: {},
          completed: true,
        }),
      })
      if (!res.ok) throw new Error('保存失败')
      // 更新缓存用户头像
      const user = getCachedUser()
      if (user) {
        const url = avatarUrl(avatarStyle, avatarSeed)
        setCachedUser({ ...user, avatar: url, mbti: type })
      }
      navigate('/', { replace: true })
    } catch (e) {
      setError(e.message || '保存失败，请重试')
      setSaving(false)
    }
  }

  const stepLabels = ['MBTI 快测', '情感风格', '兴趣爱好', '选个头像']

  return (
    <div style={s.page}>
      {/* 顶部进度 */}
      <div style={s.header}>
        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.45)', marginBottom: '8px' }}>
          步骤 {step + 1} / {TOTAL_STEPS} — {stepLabels[step]}
        </div>
        <div style={s.progress}>
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <div key={i} style={s.progressDot(i === step, i < step)} />
          ))}
        </div>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.35)' }}>
          完成后解锁「匹配度」功能 ✨
        </div>
      </div>

      {/* ── STEP 0: MBTI ── */}
      {step === 0 && (
        <div style={s.card}>
          {!mbtiDone ? (
            <>
              <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginBottom: '8px' }}>
                第 {mbtiQ + 1} / {MBTI_QUESTIONS.length} 题
              </div>
              <div style={s.question}>{MBTI_QUESTIONS[mbtiQ].q}</div>
              <div style={s.choiceRow}>
                {MBTI_QUESTIONS[mbtiQ].a.map((text, i) => (
                  <button
                    key={i}
                    style={s.choiceBtn(mbtiAnswers[mbtiQ] === i)}
                    onClick={() => handleMBTIChoice(i)}
                  >
                    <span style={{
                      width: '24px', height: '24px', borderRadius: '50%', flexShrink: 0,
                      background: mbtiAnswers[mbtiQ] === i ? '#7c6aff' : 'rgba(255,255,255,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '12px', fontWeight: 700,
                    }}>
                      {mbtiAnswers[mbtiQ] === i ? '✓' : String.fromCharCode(65 + i)}
                    </span>
                    {text}
                  </button>
                ))}
              </div>
              {mbtiQ > 0 && (
                <button style={{ ...s.backBtn, marginTop: '16px', fontSize: '13px' }}
                  onClick={() => setMbtiQ(q => q - 1)}>
                  ← 上一题
                </button>
              )}
            </>
          ) : (
            <>
              <div style={{ textAlign: 'center', padding: '12px 0 24px' }}>
                <div style={{ fontSize: '48px', marginBottom: '12px' }}>🎉</div>
                <div style={{ fontSize: '28px', fontWeight: 800, color: '#a78bfa', marginBottom: '8px' }}>
                  {computeMBTI(mbtiAnswers).type}
                </div>
                <div style={{ fontSize: '15px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.6 }}>
                  MBTI 快测完成！这只是一个参考起点，<br />你的情感世界远比 4 个字母丰富。
                </div>
              </div>
              <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', flexWrap: 'wrap' }}>
                {Object.entries(computeMBTI(mbtiAnswers).vector).map(([k, v]) => (
                  <span key={k} style={{
                    padding: '4px 10px', borderRadius: '20px', fontSize: '13px',
                    background: 'rgba(124,106,255,0.2)', border: '1px solid rgba(124,106,255,0.4)',
                  }}>{k}: {v}</span>
                ))}
              </div>
            </>
          )}
          <div style={s.navRow}>
            <button style={s.nextBtn(!mbtiDone)} disabled={!mbtiDone}
              onClick={() => setStep(1)}>
              下一步 →
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 1: 情感风格 ── */}
      {step === 1 && (
        <div style={s.card}>
          <div style={s.title}>你的情感风格</div>
          <div style={s.subtitle}>选择最符合你的一种方式，这将影响你的匹配结果</div>
          <div style={s.styleGrid}>
            {EMOTION_STYLES.map(opt => (
              <div key={opt.id} style={s.styleCard(emotionStyle === opt.id)}
                onClick={() => setEmotionStyle(opt.id)}>
                <div style={{ fontSize: '24px', marginBottom: '6px' }}>{opt.icon}</div>
                <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>{opt.label}</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', lineHeight: 1.4 }}>{opt.desc}</div>
              </div>
            ))}
          </div>
          <div style={s.navRow}>
            <button style={s.backBtn} onClick={() => setStep(0)}>← 返回</button>
            <button style={s.nextBtn(!emotionStyle)} disabled={!emotionStyle}
              onClick={() => setStep(2)}>
              下一步 →
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 2: 兴趣标签 ── */}
      {step === 2 && (
        <div style={s.card}>
          <div style={s.title}>你的兴趣爱好</div>
          <div style={s.subtitle}>最多选 8 个，已选 {interests.length} / 8</div>
          <div style={s.tagGrid}>
            {INTEREST_OPTIONS.map(opt => (
              <div key={opt.id} style={s.tag(interests.includes(opt.id))}
                onClick={() => toggleInterest(opt.id)}>
                <div style={{ fontSize: '22px', marginBottom: '4px' }}>{opt.icon}</div>
                <div>{opt.label}</div>
              </div>
            ))}
          </div>
          <div style={s.navRow}>
            <button style={s.backBtn} onClick={() => setStep(1)}>← 返回</button>
            <button style={s.nextBtn(interests.length === 0)} disabled={interests.length === 0}
              onClick={() => setStep(3)}>
              下一步 →
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 3: 头像 ── */}
      {step === 3 && (
        <div style={s.card}>
          <div style={s.title}>选一个头像</div>
          <div style={s.subtitle}>插画风格头像，随时可以在设置里更换</div>

          {/* 风格切换 */}
          <div style={s.avatarStyleRow}>
            {AVATAR_STYLES.map(st => (
              <button key={st.id} style={s.avatarStyleChip(avatarStyle === st.id)}
                onClick={() => setAvatarStyle(st.id)}>
                {st.emoji} {st.label}
              </button>
            ))}
          </div>

          {/* 头像网格 */}
          <div style={s.avatarGrid}>
            {AVATAR_SEEDS.map(seed => (
              <div key={seed} style={s.avatarItem(avatarSeed === seed)}
                onClick={() => setAvatarSeed(seed)}>
                <img
                  src={avatarUrl(avatarStyle, seed)}
                  alt={seed}
                  style={{ width: 60, height: 60, borderRadius: '50%' }}
                  loading="lazy"
                />
              </div>
            ))}
          </div>

          {/* 当前选中预览 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '20px',
            padding: '12px 14px', borderRadius: '14px', background: 'rgba(124,106,255,0.1)',
            border: '1px solid rgba(124,106,255,0.2)' }}>
            <img src={avatarUrl(avatarStyle, avatarSeed)} alt="preview"
              style={{ width: 48, height: 48, borderRadius: '50%' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '15px' }}>已选头像</div>
              <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
                {AVATAR_STYLES.find(s => s.id === avatarStyle)?.label} 风格
              </div>
            </div>
          </div>

          {error && (
            <div style={{ marginTop: '12px', color: '#ff6b6b', fontSize: '14px', textAlign: 'center' }}>
              {error}
            </div>
          )}
          <div style={s.navRow}>
            <button style={s.backBtn} onClick={() => setStep(2)}>← 返回</button>
            <button style={s.nextBtn(saving)} disabled={saving} onClick={handleSubmit}>
              {saving ? '保存中...' : '完成，进入星球 🚀'}
            </button>
          </div>
        </div>
      )}

      {/* 跳过 */}
      <button
        style={{ marginTop: '20px', background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)',
          fontSize: '13px', cursor: 'pointer' }}
        onClick={async () => {
          const token = getToken()
          if (token) {
            await fetch(`${API_BASE}/profile/survey`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ completed: true }),
            }).catch(() => {})
          }
          navigate('/', { replace: true })
        }}
      >
        跳过，稍后再填
      </button>
    </div>
  )
}
