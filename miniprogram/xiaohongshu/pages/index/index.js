const api = require('../../utils/api')

Page({
  data: {
    emotions: [],
    selectedEmotion: '',
    queryText: '我感到很痛苦，也很想被安慰，但仍然想抓住一点盼望',
    loading: false,
    verses: [],
    degraded: false,
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
      .catch(() => console.warn('[xhs] failed to load emotions'))
  },

  selectEmotion(e) {
    const emotion = e.currentTarget.dataset.emotion
    this.setData({ selectedEmotion: emotion, queryText: `我正在经历${emotion}的情绪` })
  },

  onQueryInput(e) {
    this.setData({ queryText: e.detail.value })
  },

  noop() {},

  runQuery() {
    const { queryText } = this.data
    if (!queryText.trim()) {
      my.showToast({ content: '请输入你的感受', type: 'none' })
      return
    }
    this.setData({ loading: true, verses: [], degraded: false })
    api.queryVerses(queryText)
      .then((data) => {
        if (data.degraded) { this.setData({ degraded: true }); return }
        const cuv = (data.verse_summary && data.verse_summary.cuv) || []
        this.setData({ verses: cuv })
      })
      .catch(() => {
        this.setData({ degraded: true })
        my.showToast({ content: '网络错误，请重试', type: 'none' })
      })
      .finally(() => this.setData({ loading: false }))
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
      .catch(() => this.setData({ storyError: '故事生成失败，请重试', storyText: '' }))
      .finally(() => this.setData({ storyLoading: false }))
  },

  retryStory() {
    const { selectedEmotion } = this.data
    if (!selectedEmotion) return
    this.setData({ storyText: '', storyError: '', storyLoading: true })
    this._fetchStory(selectedEmotion)
  },

  closeStory() {
    this.setData({ showStory: false, speaking: false })
  },

  speakStory() {
    const { speaking, storyText } = this.data
    if (speaking || !storyText) return
    this.setData({ speaking: true })
    if (my.tts) {
      my.tts({
        content: storyText,
        success: () => this.setData({ speaking: false }),
        fail: () => {
          my.showToast({ content: '语音播放失败', type: 'none' })
          this.setData({ speaking: false })
        },
      })
    } else {
      my.showToast({ content: '当前版本不支持语音', type: 'none' })
      this.setData({ speaking: false })
    }
  },
})
