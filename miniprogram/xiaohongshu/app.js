App({
  globalData: {
    userInfo: null,
    token: null,
    apiBase: 'https://stephenzao-emotion-sphere.hf.space/api',
  },

  onLaunch() {
    try {
      const token = my.getStorageSync({ key: 'token' }).data
      if (token) this.globalData.token = token
    } catch (e) {}
    try {
      const info = my.getStorageSync({ key: 'userInfo' }).data
      if (info) this.globalData.userInfo = info
    } catch (e) {}
  },

  requireLogin() {
    if (!this.globalData.token) {
      my.navigateTo({ url: '/pages/login/login' })
      return false
    }
    return true
  },
})
