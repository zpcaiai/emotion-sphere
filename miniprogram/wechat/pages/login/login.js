const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    loading: false,
    error: '',
  },

  onLoad() {
    // 若已有 token，直接跳主页
    if (app.globalData.token) {
      this._goHome()
    }
  },

  onLogin() {
    if (this.data.loading) return
    this.setData({ loading: true, error: '' })

    api.wxLogin()
      .then(() => {
        this._goHome()
      })
      .catch((err) => {
        this.setData({ error: err.message || '登录失败，请重试' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  _goHome() {
    wx.switchTab({ url: '/pages/index/index' })
  },
})
