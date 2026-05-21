const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    emotions: [],
    selectedEmotion: '',
    queryText: '我感到很痛苦，也很想被安慰，但仍然想抓住一点盼望',
    loading: false,
    verses: [],
    degraded: false,
    // story
    showStory: false,
    storyLoading: false,
    storyError: '',
    storyText: '',
    speaking: false,
  },

  onLoad() {
    this._loadEmotions()
  },

  _loadEmotions() {
    api.fetchLayout()
      .then((data) => {
        const items = (data && data.items) || []
        this.setData({ emotions: items.slice(0, 60) })
      })
      .catch(() => {
        console.warn('[miniprogram] failed to load emotions layout')
      })
  },

  selectEmotion(e) {
    const emotion = e.currentTarget.dataset.emotion
    this.setData({ selectedEmotion: emotion, queryText: `我正在经历${emotion}的情绪` })
  },

  onQueryInput(e) {
    this.setData({ queryText: e.detail.value })
  },

  runQuery() {
    const { queryText } = this.data
    if (!queryText.trim()) {
      wx.showToast({ title: '请输入你的感受', icon: 'none' })
      return
    }
    this.setData({ loading: true, verses: [], degraded: false })
    api.queryVerses(queryText)
      .then((data) => {
        if (data.degraded) {
          this.setData({ degraded: true, verses: [] })
          return
        }
        const cuv = (data.verse_summary && data.verse_summary.cuv) || []
        this.setData({ verses: cuv })
      })
      .catch(() => {
        this.setData({ degraded: true })
        wx.showToast({ title: '网络错误，请重试', icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  openStory() {
    const { selectedEmotion } = this.data
    if (!selectedEmotion) return
    this.setData({ showStory: true, storyText: '', storyError: '', storyLoading: true })
    this._fetchStory(selectedEmotion)
  },

  _fetchStory(emotion) {
    api.fetchStory(emotion)
      .then((data) => {
        this.setData({ storyText: data.story || `愿在"${emotion}"中，你找到一丝平静与力量。` })
      })
      .catch(() => {
        this.setData({ storyError: '故事生成失败，请重试', storyText: '' })
      })
      .finally(() => {
        this.setData({ storyLoading: false })
      })
  },

  retryStory() {
    const { selectedEmotion } = this.data
    if (!selectedEmotion) return
    this.setData({ storyText: '', storyError: '', storyLoading: true })
    this._fetchStory(selectedEmotion)
  },

  closeStory() {
    this._stopSpeak()
    this.setData({ showStory: false, speaking: false })
  },

  speakStory() {
    const { speaking, storyText } = this.data
    if (speaking) { this._stopSpeak(); return }
    if (!storyText) return
    wx.createInnerAudioContext && this._speakWithTTS(storyText)
  },

  _speakWithTTS(text) {
    if (wx.getSystemInfoSync().platform === 'devtools') {
      wx.showToast({ title: '开发工具暂不支持语音', icon: 'none' })
      return
    }
    this.setData({ speaking: true })
    if (wx.textToSpeech) {
      wx.textToSpeech({
        lang: 'zh_CN', speed: 1.0, content: text,
        success: () => this.setData({ speaking: false }),
        fail: () => {
          wx.showToast({ title: '语音播放失败', icon: 'none' })
          this.setData({ speaking: false })
        },
      })
    } else {
      wx.showToast({ title: '当前版本不支持语音', icon: 'none' })
      this.setData({ speaking: false })
    }
  },

  _stopSpeak() {
    this.setData({ speaking: false })
  },
})
