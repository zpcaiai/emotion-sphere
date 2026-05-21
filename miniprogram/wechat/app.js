App({
  globalData: {
    userInfo: null,
    token: null,
    apiBase: 'https://stephenzao-emotion-sphere.hf.space/api',
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
    }
    try {
      const cached = wx.getStorageSync('userInfo')
      if (cached) this.globalData.userInfo = cached
    } catch (e) {}
  },

  /**
   * 检查是否已登录，未登录则跳转登录页。
   * 供各页面 onShow/onLoad 调用。
   * @returns {boolean} 是否已登录
   */
  requireLogin() {
    if (!this.globalData.token) {
      wx.navigateTo({ url: '/pages/login/login' })
      return false
    }
    return true
  },
})
