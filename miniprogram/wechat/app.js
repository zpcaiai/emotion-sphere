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
  },
})
