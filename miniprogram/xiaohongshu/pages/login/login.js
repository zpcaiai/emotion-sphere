const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    loading: false,
    error: '',
  },

  onLoad() {
    if (app.globalData.token) {
      this._goHome()
    }
  },

  onLogin() {
    if (this.data.loading) return
    this.setData({ loading: true, error: '' })
    api.xhsLogin()
      .then(() => { this._goHome() })
      .catch((err) => { this.setData({ error: err.message || '登录失败，请重试' }) })
      .finally(() => { this.setData({ loading: false }) })
  },

  _goHome() {
    my.switchTab({ url: '/pages/index/index' })
  },
})
