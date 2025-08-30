// flip-test.js - 卡片翻转测试页面
Page({
  data: {
    isFlipped: false
  },

  onLoad() {
    console.log('翻转测试页面加载完成');
  },

  /**
   * 翻转卡片
   */
  flipCard() {
    console.log('翻转卡片，当前状态：', this.data.isFlipped);
    
    this.setData({
      isFlipped: !this.data.isFlipped
    });

    // 显示当前状态
    wx.showToast({
      title: this.data.isFlipped ? '已翻转到背面' : '已翻转到正面',
      icon: 'none',
      duration: 1000
    });
  },

  /**
   * 返回上一页
   */
  goBack() {
    wx.navigateBack();
  }
});