// 明信片交互脚本
class PostcardApp {
    constructor() {
        this.postcard = document.getElementById('postcard');
        this.soundControl = document.getElementById('soundControl');
        this.isFlipped = false;
        this.soundEnabled = true;
        this.particles = [];
        
        this.init();
    }
    
    init() {
        this.createParticles();
        this.bindEvents();
        this.setCurrentDate();
        this.startAnimations();
        this.playWelcomeSound();
    }
    
    // 创建粒子效果
    createParticles() {
        const particlesContainer = document.getElementById('particles');
        const particleCount = window.innerWidth < 768 ? 30 : 50;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // 随机位置
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            
            // 随机动画延迟
            particle.style.animationDelay = Math.random() * 6 + 's';
            particle.style.animationDuration = (Math.random() * 3 + 4) + 's';
            
            // 随机大小
            const size = Math.random() * 4 + 2;
            particle.style.width = size + 'px';
            particle.style.height = size + 'px';
            
            particlesContainer.appendChild(particle);
            this.particles.push(particle);
        }
    }
    
    // 绑定事件
    bindEvents() {
        // 明信片点击事件
        this.postcard.addEventListener('click', (e) => {
            this.flipCard();
            this.playFlipSound();
        });
        
        // 明信片触摸事件（移动端）
        this.postcard.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.postcard.style.transform = 'scale(0.98)';
        });
        
        this.postcard.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.postcard.style.transform = 'scale(1)';
            this.flipCard();
            this.playFlipSound();
        });
        
        // 音效控制
        this.soundControl.addEventListener('click', () => {
            this.toggleSound();
        });
        
        // 键盘事件
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' || e.code === 'Enter') {
                e.preventDefault();
                this.flipCard();
                this.playFlipSound();
            }
        });
        
        // 窗口调整事件
        window.addEventListener('resize', () => {
            this.adjustForScreenSize();
        });
        
        // 鼠标悬停效果
        this.postcard.addEventListener('mouseenter', () => {
            this.addHoverEffect();
        });
        
        this.postcard.addEventListener('mouseleave', () => {
            this.removeHoverEffect();
        });
    }
    
    // 翻转明信片
    flipCard() {
        this.isFlipped = !this.isFlipped;
        
        if (this.isFlipped) {
            this.postcard.classList.add('flipped');
        } else {
            this.postcard.classList.remove('flipped');
        }
        
        // 添加翻转震动效果（支持的设备）
        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
        
        // 更新装饰动画
        this.updateDecorations();
    }
    
    // 设置当前日期
    setCurrentDate() {
        const dateElement = document.querySelector('.date');
        const now = new Date();
        const options = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        };
        dateElement.textContent = now.toLocaleDateString('zh-CN', options);
    }
    
    // 开始动画
    startAnimations() {
        // 延迟显示装饰元素
        setTimeout(() => {
            const decorations = document.querySelectorAll('.decorations .heart, .decorations .star');
            decorations.forEach((elem, index) => {
                setTimeout(() => {
                    elem.style.opacity = '1';
                    elem.style.animation += ', fadeIn 0.5s ease-out';
                }, index * 200);
            });
        }, 2000);
        
        // 周期性粒子效果更新
        setInterval(() => {
            this.updateParticles();
        }, 8000);
    }
    
    // 更新粒子效果
    updateParticles() {
        this.particles.forEach(particle => {
            // 随机改变粒子位置
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            
            // 随机改变动画延迟
            particle.style.animationDelay = Math.random() * 6 + 's';
        });
    }
    
    // 更新装饰元素
    updateDecorations() {
        const decorations = document.querySelectorAll('.decorations .heart, .decorations .star');
        decorations.forEach(elem => {
            elem.style.animationDuration = this.isFlipped ? '2s' : '4s';
        });
    }
    
    // 添加悬停效果
    addHoverEffect() {
        this.postcard.style.transform += ' translateY(-5px)';
        this.postcard.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.4)';
    }
    
    // 移除悬停效果
    removeHoverEffect() {
        const currentTransform = this.postcard.style.transform.replace(' translateY(-5px)', '');
        this.postcard.style.transform = currentTransform;
        this.postcard.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.3)';
    }
    
    // 播放翻转音效
    playFlipSound() {
        if (!this.soundEnabled) return;
        
        // 使用Web Audio API创建翻转音效
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(200, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            console.log('音效播放失败:', e);
        }
    }
    
    // 播放欢迎音效
    playWelcomeSound() {
        if (!this.soundEnabled) return;
        
        setTimeout(() => {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                // 播放一个愉快的和弦
                oscillator.frequency.setValueAtTime(523, audioContext.currentTime); // C5
                oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.2); // E5
                oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.4); // G5
                
                gainNode.gain.setValueAtTime(0.05, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.6);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.6);
            } catch (e) {
                console.log('欢迎音效播放失败:', e);
            }
        }, 1500);
    }
    
    // 切换音效
    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        const soundIcon = document.querySelector('.sound-icon');
        soundIcon.textContent = this.soundEnabled ? '🔊' : '🔇';
        
        // 播放切换提示音
        if (this.soundEnabled) {
            this.playFlipSound();
        }
    }
    
    // 屏幕尺寸适配
    adjustForScreenSize() {
        const width = window.innerWidth;
        const postcard = this.postcard;
        
        if (width < 360) {
            postcard.style.transform = 'scale(0.9)';
        } else if (width < 480) {
            postcard.style.transform = 'scale(0.95)';
        } else {
            postcard.style.transform = 'scale(1)';
        }
    }
    
    // 创建特效
    createSparkleEffect(x, y) {
        for (let i = 0; i < 6; i++) {
            const sparkle = document.createElement('div');
            sparkle.style.position = 'absolute';
            sparkle.style.left = x + 'px';
            sparkle.style.top = y + 'px';
            sparkle.style.width = '4px';
            sparkle.style.height = '4px';
            sparkle.style.background = '#ffd700';
            sparkle.style.borderRadius = '50%';
            sparkle.style.pointerEvents = 'none';
            sparkle.style.zIndex = '1000';
            
            const angle = (i * 60) * Math.PI / 180;
            const distance = 20;
            const endX = x + Math.cos(angle) * distance;
            const endY = y + Math.sin(angle) * distance;
            
            sparkle.animate([
                { transform: 'translate(0, 0) scale(1)', opacity: 1 },
                { transform: `translate(${endX - x}px, ${endY - y}px) scale(0)`, opacity: 0 }
            ], {
                duration: 800,
                easing: 'ease-out'
            }).onfinish = () => sparkle.remove();
            
            document.body.appendChild(sparkle);
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否支持触摸
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    if (isTouchDevice) {
        document.body.classList.add('touch-device');
    }
    
    // 初始化明信片应用
    new PostcardApp();
    
    // 添加加载完成提示
    setTimeout(() => {
        const hint = document.createElement('div');
        hint.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        hint.textContent = '点击明信片可以翻转哦！';
        document.body.appendChild(hint);
        
        // 显示提示
        setTimeout(() => hint.style.opacity = '1', 100);
        
        // 3秒后隐藏提示
        setTimeout(() => {
            hint.style.opacity = '0';
            setTimeout(() => hint.remove(), 300);
        }, 3000);
    }, 500);
});

// 防止页面被意外刷新
window.addEventListener('beforeunload', (e) => {
    // 在某些浏览器中显示确认对话框
    e.preventDefault();
    e.returnValue = '';
});

// 处理页面可见性变化
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // 页面隐藏时暂停动画
        document.querySelectorAll('.particle, .heart, .star').forEach(elem => {
            elem.style.animationPlayState = 'paused';
        });
    } else {
        // 页面显示时恢复动画
        document.querySelectorAll('.particle, .heart, .star').forEach(elem => {
            elem.style.animationPlayState = 'running';
        });
    }
});