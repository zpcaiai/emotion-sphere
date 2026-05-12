import { useState, useRef, useEffect } from 'react'
import { generateStory } from './api'

const VOICES = [
  { name: 'zh-CN-XiaoxiaoNeural', label: '晓晓（温柔）' },
  { name: 'zh-CN-XiaoyiNeural', label: '晓依（知性）' },
  { name: 'zh-CN-XiaohanNeural', label: '晓涵（沉稳）' },
]

function useVoicePlayer(text) {
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const uttRef = useRef(null)
  const timerRef = useRef(null)

  const stop = () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel()
    clearInterval(timerRef.current)
    setPlaying(false)
    setProgress(0)
    uttRef.current = null
  }

  const play = (voiceName) => {
    if (!text || !window.speechSynthesis) return
    stop()
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'zh-CN'
    utt.rate = 0.9
    utt.pitch = 1.1
    const voices = window.speechSynthesis.getVoices()
    const match = voices.find((v) => v.name === voiceName || v.lang === 'zh-CN')
    if (match) utt.voice = match
    utt.onend = () => { setPlaying(false); setProgress(100); clearInterval(timerRef.current) }
    utt.onerror = () => { setPlaying(false); setProgress(0); clearInterval(timerRef.current) }
    uttRef.current = utt
    window.speechSynthesis.speak(utt)
    setPlaying(true)
    setProgress(0)
    const charTotal = text.length
    let charDone = 0
    utt.onboundary = (e) => {
      charDone = e.charIndex || charDone
      setProgress(Math.min(99, Math.round((charDone / charTotal) * 100)))
    }
    timerRef.current = setInterval(() => {
      if (!window.speechSynthesis.speaking) { clearInterval(timerRef.current); setPlaying(false) }
    }, 500)
  }

  useEffect(() => () => stop(), [])

  return { playing, progress, play, stop }
}

export default function StoryCard({ emotion, onClose }) {
  const [story, setStory] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [generated, setGenerated] = useState(false)
  const [copied, setCopied] = useState(false)
  const [voiceIndex, setVoiceIndex] = useState(0)
  const { playing, progress, play, stop } = useVoicePlayer(story)

  const generate = async () => {
    setLoading(true)
    setError('')
    setStory('')
    setGenerated(false)
    try {
      const data = await generateStory(emotion)
      setStory(data.story || data.text || JSON.stringify(data))
      setGenerated(true)
    } catch (err) {
      setError(err.message || '生成失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { generate() }, [])

  const copyStory = () => {
    if (!story) return
    navigator.clipboard.writeText(story).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const cardStyle = {
    position: 'fixed', inset: 0, zIndex: 2000,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)',
  }
  const innerStyle = {
    width: '90%', maxWidth: 480, maxHeight: '85vh',
    background: 'linear-gradient(160deg,#1a1a2e 0%,#16213e 100%)',
    borderRadius: 20, border: '1px solid rgba(255,255,255,0.12)',
    boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  }
  const headerStyle = {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)',
  }
  const titleStyle = { color: '#fff', fontSize: 16, fontWeight: 600, margin: 0 }
  const closeBtn = {
    background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
    fontSize: 22, cursor: 'pointer', lineHeight: 1, padding: '0 4px',
  }
  const bodyStyle = {
    flex: 1, overflowY: 'auto', padding: '16px 20px',
    scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.15) transparent',
  }
  const storyTextStyle = {
    color: 'rgba(255,255,255,0.88)', fontSize: 15, lineHeight: 1.85,
    whiteSpace: 'pre-wrap', margin: 0,
  }
  const loadingStyle = {
    color: 'rgba(255,255,255,0.5)', textAlign: 'center', padding: '40px 0', fontSize: 15,
  }
  const errorStyle = {
    color: '#ff6b6b', textAlign: 'center', padding: '20px 0', fontSize: 14,
  }
  const progressTrack = {
    height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2,
    margin: '0 20px 8px', overflow: 'hidden',
  }
  const progressFill = {
    height: '100%', width: `${progress}%`,
    background: 'linear-gradient(90deg,#f093fb,#f5576c)',
    borderRadius: 2, transition: 'width 0.3s',
  }
  const voiceBarStyle = {
    padding: '10px 20px', borderTop: '1px solid rgba(255,255,255,0.08)',
    display: 'flex', alignItems: 'center', gap: 10,
  }
  const footerStyle = {
    padding: '10px 20px 16px', borderTop: '1px solid rgba(255,255,255,0.08)',
    display: 'flex', gap: 10,
  }
  const btnBase = {
    flex: 1, padding: '9px 0', borderRadius: 12, border: 'none',
    fontSize: 13, fontWeight: 500, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
  }
  const primaryBtn = { ...btnBase, background: 'linear-gradient(135deg,#f093fb,#f5576c)', color: '#fff' }
  const secondaryBtn = { ...btnBase, background: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.8)' }
  const selectStyle = {
    flex: 1, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8, color: '#fff', fontSize: 12, padding: '5px 8px', cursor: 'pointer',
  }
  const playBtn = {
    ...btnBase, flex: 'none', width: 36, height: 36,
    borderRadius: '50%', padding: 0,
    background: playing
      ? 'linear-gradient(135deg,#ff9500,#ff6b35)'
      : 'linear-gradient(135deg,#34c759,#30d158)',
  }

  return (
    <div style={cardStyle} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={innerStyle}>
        <div style={headerStyle}>
          <p style={titleStyle}>✨ {emotion} · 励志故事</p>
          <button style={closeBtn} onClick={onClose}>×</button>
        </div>

        <div style={bodyStyle}>
          {loading && <p style={loadingStyle}>正在生成专属故事…</p>}
          {error && <p style={errorStyle}>{error}</p>}
          {story && <p style={storyTextStyle}>{story}</p>}
        </div>

        {story && (
          <>
            <div style={progressTrack}><div style={progressFill} /></div>
            <div style={voiceBarStyle}>
              <button
                style={playBtn}
                onClick={() => playing ? stop() : play(VOICES[voiceIndex].name)}
                title={playing ? '停止' : '播放'}
              >
                {playing ? '⏹' : '▶'}
              </button>
              <select
                style={selectStyle}
                value={voiceIndex}
                onChange={(e) => { stop(); setVoiceIndex(Number(e.target.value)) }}
              >
                {VOICES.map((v, i) => <option key={v.name} value={i}>{v.label}</option>)}
              </select>
            </div>
          </>
        )}

        <div style={footerStyle}>
          {generated && (
            <button style={secondaryBtn} onClick={copyStory}>
              {copied ? '✓ 已复制' : '📋 复制'}
            </button>
          )}
          <button style={secondaryBtn} onClick={generate} disabled={loading}>
            {loading ? '生成中…' : '🔄 重新生成'}
          </button>
          <button style={primaryBtn} onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  )
}
