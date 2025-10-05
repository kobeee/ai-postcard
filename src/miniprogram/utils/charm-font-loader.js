// utils/charm-font-loader.js - 专用于挂件正反面的书法字体加载
const envConfig = require('../config/env.js');
const { resourceCache } = require('./resource-cache.js');

const CHARM_FONT_MANIFEST = [
  { family: 'MaShanZheng', file: 'ma-shan-zheng-6500.woff', weight: '400' },
  { family: 'ZhiMangXing', file: 'zhi-mang-xing-6500.woff', weight: '400' },
  { family: 'LongCang', file: 'long-cang-6500.woff', weight: '400' }
];

const loadedFontFamilies = new Set();
let loadPromise = null;

const normalizeBaseUrl = (url) => {
  if (!url || typeof url !== 'string') {
    return 'http://localhost:8080';
  }
  return url.replace(/\/+$/, '');
};

const readFileAsBase64 = (filePath) => {
  return new Promise((resolve, reject) => {
    const fs = wx.getFileSystemManager();
    fs.readFile({
      filePath,
      encoding: 'base64',
      success: (res) => resolve(res.data),
      fail: reject
    });
  });
};

const buildFontSource = async (cachedPath, remoteUrl) => {
  if (!cachedPath) {
    return `url("${remoteUrl}")`;
  }

  if (/^https?:\/\//i.test(cachedPath)) {
    return `url("${cachedPath}")`;
  }

  try {
    const base64Data = await readFileAsBase64(cachedPath);
    return `url("data:font/woff;base64,${base64Data}")`;
  } catch (error) {
    envConfig.error('字体本地读取失败，回退使用远程地址', error);
    return `url("${remoteUrl}")`;
  }
};

const loadSingleFont = async (fontMeta) => {
  if (loadedFontFamilies.has(fontMeta.family)) {
    return { font: fontMeta.family, status: 'cached' };
  }

  const baseUrl = normalizeBaseUrl(envConfig.AI_AGENT_PUBLIC_URL || 'http://localhost:8080');
  const fontUrl = `${baseUrl}/resources/font/${encodeURIComponent(fontMeta.file)}`;

  try {
    const cachedPath = await resourceCache.getCachedResourceUrl(fontUrl);
    const fontSource = await buildFontSource(cachedPath, fontUrl);

    await new Promise((resolve, reject) => {
      wx.loadFontFace({
        family: fontMeta.family,
        source: fontSource,
        global: false,
        scopes: ['webview', 'native'],
        desc: { style: 'normal', weight: fontMeta.weight || '400' },
        success: (res) => {
          loadedFontFamilies.add(fontMeta.family);
          envConfig.log(`✅ 挂件字体 ${fontMeta.family} 加载成功`, res.status);
          resolve(res);
        },
        fail: (err) => {
          envConfig.error(`❌ 挂件字体 ${fontMeta.family} 加载失败`, err);
          reject(err);
        }
      });
    });

    return { font: fontMeta.family, status: 'loaded' };
  } catch (error) {
    envConfig.warn(`⚠️ 挂件字体 ${fontMeta.family} 加载过程中出现问题，将回退系统字体`, error);
    return { font: fontMeta.family, status: 'failed', error };
  }
};

const loadFontSet = async () => {
  const results = await Promise.all(CHARM_FONT_MANIFEST.map(loadSingleFont));
  const hasFailure = results.some(result => result.status === 'failed');

  if (hasFailure) {
    // 允许后续视情况重新尝试加载失败的字体
    loadPromise = null;
  }

  return results;
};

const loadCharmFontsOnce = () => {
  if (!loadPromise) {
    loadPromise = loadFontSet().catch((error) => {
      // 如果整体失败，允许后续再次尝试
      loadPromise = null;
      throw error;
    });
  }
  return loadPromise;
};

module.exports = {
  loadCharmFontsOnce,
  CHARM_FONT_MANIFEST
};
