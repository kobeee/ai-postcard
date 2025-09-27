import logging
import json
import random
from typing import Dict, Any
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class MiniprogramComponentGenerator:
    """小程序挂件组件生成器 - 第5步：生成心象签挂件的WXML/WXSS/JS代码"""
    
    def __init__(self):
        # 使用Gemini进行小程序组件代码生成
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成心象签小程序挂件组件代码"""
        try:
            task = context["task"]
            results = context["results"]
            
            self.logger.info("🔮 开始生成心象签小程序挂件组件...")
            
            # 获取之前步骤的结果
            structured_data = results.get("structured_data", {})
            selected_charm = results.get("selected_charm_style", {})
            image_url = results.get("image_url", "")
            
            # 构建小程序组件生成提示词
            component_prompt = self._build_miniprogram_component_prompt(
                structured_data, selected_charm, image_url, task
            )
            
            # 调用Gemini生成小程序组件代码
            component_code = await self.provider.generate_text(
                prompt=component_prompt,
                max_tokens=3000,
                temperature=0.3
            )
            
            # 解析并验证组件代码
            parsed_component = self._parse_and_validate_component(component_code)
            
            # 保存结果
            results["frontend_code"] = json.dumps(parsed_component, ensure_ascii=False, indent=2)
            results["miniprogram_component"] = parsed_component
            
            self.logger.info("✅ 心象签小程序挂件组件生成完成")
            self.logger.info(f"📊 组件包含: {list(parsed_component.keys())}")
            
            context["results"] = results
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 小程序组件生成失败: {e}")
            # 使用兜底组件
            fallback_component = self._get_fallback_component(context)
            context["results"]["frontend_code"] = json.dumps(fallback_component, ensure_ascii=False, indent=2)
            context["results"]["miniprogram_component"] = fallback_component
            return context
    
    def _build_miniprogram_component_prompt(self, structured_data: Dict, selected_charm: Dict, image_url: str, task: Dict) -> str:
        """构建小程序挂件组件生成提示词"""
        
        # 提取关键信息
        oracle_theme = structured_data.get("oracle_theme", {})
        charm_identity = structured_data.get("charm_identity", {})
        oracle_manifest = structured_data.get("oracle_manifest", {})
        blessing_stream = structured_data.get("blessing_stream", [])
        ink_reading = structured_data.get("ink_reading", {})
        
        title = oracle_theme.get("title", "心象签")
        charm_name = charm_identity.get("charm_name", "安心签")
        charm_blessing = charm_identity.get("charm_blessing", "愿你心安")
        charm_main_color = charm_identity.get("main_color", "#8B7355")
        charm_accent_color = charm_identity.get("accent_color", "#D4AF37")
        
        hexagram_name = oracle_manifest.get("hexagram", {}).get("name", "和风细雨")
        hexagram_insight = oracle_manifest.get("hexagram", {}).get("insight", "心境平和")
        daily_guides = oracle_manifest.get("daily_guide", ["保持平静"])
        
        stroke_impression = ink_reading.get("stroke_impression", "笔触温和")
        
        selected_charm_name = selected_charm.get("name", "莲花圆牌 (平和雅致)")
        charm_image_path = f"/resources/签体/{selected_charm.get('image', '莲花圆牌 (平和雅致).png')}"
        
        prompt = f"""
请为微信小程序生成一个心象签挂件组件，具体要求：

**核心数据**：
- 自然意象标题：{title}
- 签名：{charm_name}
- 签体祝福：{charm_blessing}
- 卦象名称：{hexagram_name}
- 卦象解读：{hexagram_insight}
- 笔触印象：{stroke_impression}
- 日常指引：{daily_guides}
- 祝福流：{blessing_stream}
- 签体样式：{selected_charm_name}
- 挂件图片路径：{charm_image_path}
- 背景图片：{image_url}
- 主色调：{charm_main_color}
- 强调色：{charm_accent_color}

**组件功能要求**：
1. **挂件正面**：显示选中的签体图片，左上角显示签名（竖排文字），底部显示简短祝福
2. **翻转交互**：点击挂件可翻转查看解签内容
3. **解签背面**：竖排布局的解签笺，包含卦象名称、解读内容、日常指引等
4. **视觉效果**：悬挂动画、翻转3D效果、背景图片淡化显示

**技术规范**：
- 使用微信小程序的WXML、WXSS、JS格式
- 组件宽度375rpx，高度500rpx，适配手机屏幕
- 支持点击翻转，使用transform3d实现3D效果
- 文字使用楷体字体，体现传统文化特色
- 背景图片淡化处理，确保文字可读性

请生成JSON格式的组件代码，包含以下字段：
```json
{{
  "wxml": "WXML模板代码",
  "wxss": "WXSS样式代码", 
  "js": "JS逻辑代码"
}}
```

**重要细节**：
- 签名要竖排显示在挂件左上角，每个字单独一行
- 解签笺要用竖排布局，体现传统文化特色
- 背景图片要淡化处理（opacity: 0.15），不影响文字阅读
- 挂件要有悬挂的摇摆动画效果
- 翻转动画要流畅自然，使用rotateY实现

请确保代码完整可用，符合微信小程序开发规范。
"""
        
        return prompt
    
    def _parse_and_validate_component(self, component_code: str) -> Dict[str, str]:
        """解析并验证组件代码"""
        try:
            # 尝试从响应中提取JSON
            json_start = component_code.find('{')
            json_end = component_code.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = component_code[json_start:json_end]
                parsed_component = json.loads(json_str)
                
                # 验证必需字段
                required_fields = ['wxml', 'wxss', 'js']
                for field in required_fields:
                    if field not in parsed_component or not parsed_component[field]:
                        self.logger.warning(f"⚠️ 缺少组件字段：{field}")
                        
                # 确保所有字段都是字符串
                for field in required_fields:
                    if field in parsed_component and not isinstance(parsed_component[field], str):
                        parsed_component[field] = str(parsed_component[field])
                
                self.logger.info("✅ 组件代码解析成功")
                return parsed_component
            else:
                raise ValueError("无法找到有效的JSON代码")
                
        except Exception as e:
            self.logger.error(f"❌ 解析组件代码失败: {e}")
            self.logger.error(f"🐛 原始响应: {component_code[:500]}...")
            return self._get_default_component()
    
    def _get_fallback_component(self, context: Dict[str, Any]) -> Dict[str, str]:
        """获取兜底组件"""
        try:
            results = context["results"]
            structured_data = results.get("structured_data", {})
            selected_charm = results.get("selected_charm_style", {})
            
            # 从结构化数据中提取关键信息
            oracle_theme = structured_data.get("oracle_theme", {})
            charm_identity = structured_data.get("charm_identity", {})
            
            title = oracle_theme.get("title", "心象签")
            charm_name = charm_identity.get("charm_name", "安心签")
            charm_blessing = charm_identity.get("charm_blessing", "愿你心安")
            selected_charm_name = selected_charm.get("name", "莲花圆牌")
            
            return self._get_default_component(title, charm_name, charm_blessing, selected_charm_name)
            
        except Exception:
            return self._get_default_component()
    
    def _get_default_component(self, title="心象签", charm_name="安心签", charm_blessing="愿你心安", charm_style="莲花圆牌") -> Dict[str, str]:
        """获取默认的心象签组件代码"""
        
        # 随机选择一个兜底的挂件图片
        fallback_charms = [
            "莲花圆牌 (平和雅致).png",
            "金边墨玉璧 (沉稳庄重).png", 
            "青花瓷扇 (文化底蕴).png"
        ]
        selected_image = random.choice(fallback_charms)
        
        wxml = f'''<!-- 心象签挂件组件 -->
<view class="charm-scene" style="{{{{containerStyle}}}}">
  <view class="charm-flipper {{{{isFlipped ? 'flipped' : ''}}}}" bindtap="onCharmTap">
    
    <!-- 正面：挂件 -->
    <view class="charm-face charm-face-front">
      <view class="charm-container">
        <image class="charm-image" src="/resources/签体/{selected_image}" mode="aspectFit"></image>
        
        <!-- 左上角签名（竖排） -->
        <view class="charm-name-vertical" style="color: #8B7355;">
          <text class="name-char" wx:for="{{{{charmName}}}}" wx:key="*this">{{{{item}}}}</text>
        </view>
        
        <!-- 底部祝福 -->
        <view class="charm-blessing" style="color: #8B7355;">
          {{{{charmBlessing}}}}
        </view>
      </view>
      
      <!-- 翻面提示 -->
      <view class="flip-hint">
        <text class="flip-hint-text">查看解签</text>
      </view>
    </view>
    
    <!-- 背面：解签笺 -->
    <view class="charm-face charm-face-back">
      <view class="interpretation-scroll">
        <!-- 背景图片 -->
        <view class="scroll-background" wx:if="{{{{backgroundImage}}}}" 
              style="background-image: url({{{{backgroundImage}}}});"></view>
        
        <!-- 解签内容 -->
        <view class="scroll-content">
          <view class="scroll-title">
            <view class="title-char">解</view>
            <view class="title-char">签</view>
            <view class="title-char">笺</view>
          </view>
          
          <view class="hexagram-name" wx:if="{{{{hexagramName}}}}">
            <view class="hexagram-char" wx:for="{{{{hexagramName}}}}" wx:key="*this">{{{{item}}}}</view>
          </view>
          
          <view class="interpretation-text">{{{{interpretation}}}}</view>
          
          <view class="daily-guides" wx:if="{{{{dailyGuides.length > 0}}}}">
            <view class="guide-item" wx:for="{{{{dailyGuides}}}}" wx:key="*this">{{{{item}}}}</view>
          </view>
        </view>
      </view>
    </view>
    
  </view>
</view>'''

        wxss = '''/* 心象签挂件组件样式 */
.charm-scene {
  position: relative;
  width: 375rpx;
  height: 500rpx;
  margin: 0 auto;
  perspective: 1000rpx;
}

.charm-flipper {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.5s ease-in-out;
  animation: hanging 3s ease-in-out infinite alternate;
}

.charm-flipper.flipped {
  transform: rotateY(180deg);
}

@keyframes hanging {
  0% { transform: translateY(0) rotate(-1deg); }
  100% { transform: translateY(-10rpx) rotate(1deg); }
}

.charm-face {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border-radius: 20rpx;
  overflow: hidden;
}

.charm-face-front {
  z-index: 2;
  transform: rotateY(0deg);
}

.charm-face-back {
  z-index: 1;
  transform: rotateY(180deg);
  background: transparent;
}

.charm-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.charm-image {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 8rpx 24rpx rgba(0, 0, 0, 0.15));
}

.charm-name-vertical {
  position: absolute;
  top: 60rpx;
  left: 60rpx;
  writing-mode: vertical-rl;
  text-orientation: upright;
  z-index: 10;
  font-family: 'STKaiti', 'KaiTi', serif;
}

.name-char {
  display: block;
  font-size: 40rpx;
  font-weight: 600;
  line-height: 1.2;
  text-shadow: 2rpx 2rpx 6rpx rgba(0, 0, 0, 0.4);
  margin-bottom: 8rpx;
}

.charm-blessing {
  position: absolute;
  bottom: 80rpx;
  left: 50%;
  transform: translateX(-50%);
  font-size: 28rpx;
  font-weight: 400;
  text-align: center;
  opacity: 0.9;
  text-shadow: 2rpx 2rpx 4rpx rgba(0, 0, 0, 0.2);
}

.flip-hint {
  position: absolute;
  bottom: 20rpx;
  left: 50%;
  transform: translateX(-50%);
  padding: 8rpx 16rpx;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16rpx;
  font-size: 20rpx;
  color: #666;
  opacity: 0.8;
}

/* 解签笺样式 */
.interpretation-scroll {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 320rpx;
  height: 450rpx;
  transform: translate(-50%, -50%);
  background: #ffffff;
  border-radius: 20rpx;
  box-shadow: 0 16rpx 48rpx rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.scroll-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  opacity: 0.15;
  filter: blur(2rpx);
  z-index: -1;
}

.scroll-content {
  padding: 40rpx 30rpx;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.scroll-title {
  font-family: 'STKaiti', 'KaiTi', serif;
  margin-bottom: 30rpx;
}

.title-char {
  font-size: 36rpx;
  font-weight: 600;
  color: #2F2A26;
  line-height: 1.4;
  margin-bottom: 8rpx;
}

.hexagram-name {
  margin-bottom: 25rpx;
}

.hexagram-char {
  font-size: 48rpx;
  font-weight: 600;
  color: #1F2937;
  font-family: 'STKaiti', 'KaiTi', serif;
  line-height: 1.2;
  margin-bottom: 6rpx;
}

.interpretation-text {
  font-size: 24rpx;
  color: #4B5563;
  line-height: 1.6;
  margin-bottom: 25rpx;
  text-align: center;
}

.daily-guides {
  margin-top: auto;
}

.guide-item {
  font-size: 22rpx;
  color: #6B7280;
  line-height: 1.5;
  margin-bottom: 8rpx;
  opacity: 0.8;
}'''

        js = f'''// 心象签挂件组件逻辑
Component({{
  properties: {{
    // 签名
    charmName: {{
      type: String,
      value: '{charm_name}'
    }},
    // 签体祝福
    charmBlessing: {{
      type: String,
      value: '{charm_blessing}'
    }},
    // 卦象名称
    hexagramName: {{
      type: String,
      value: ''
    }},
    // 解签内容
    interpretation: {{
      type: String,
      value: '心境平和，万事如意'
    }},
    // 日常指引
    dailyGuides: {{
      type: Array,
      value: ['保持内心平静', '关注身边美好']
    }},
    // 背景图片
    backgroundImage: {{
      type: String,
      value: ''
    }},
    // 容器样式
    containerStyle: {{
      type: String,
      value: ''
    }}
  }},
  
  data: {{
    isFlipped: false
  }},
  
  methods: {{
    // 点击翻转挂件
    onCharmTap() {{
      this.setData({{
        isFlipped: !this.data.isFlipped
      }});
      
      // 触发自定义事件
      this.triggerEvent('charFlip', {{
        isFlipped: !this.data.isFlipped
      }});
    }},
    
    // 重置到正面
    resetToFront() {{
      this.setData({{
        isFlipped: false
      }});
    }}
  }},
  
  lifetimes: {{
    attached() {{
      console.log('心象签挂件组件已加载');
    }}
  }}
}});'''

        return {
            "wxml": wxml,
            "wxss": wxss, 
            "js": js
        }