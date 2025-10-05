// utils/charm-font-loader.js - 专用于挂件正反面的书法字体加载
const envConfig = require('../config/env.js');
const { resourceCache } = require('./resource-cache.js');

const CHARM_FONT_MANIFEST = [
  { family: 'MaShanZheng', file: 'ma-shan-zheng-6500.woff', weight: '400' },
  { family: 'ZhiMangXing', file: 'zhi-mang-xing-6500.woff', weight: '400' },
  { family: 'LongCang', file: 'long-cang-6500.woff', weight: '400' }
];

const GLOBAL_CONTEXT_ID = 'global';
const loadedFontContexts = new Map(); // Map<string, Set<string>>: family -> contexts
let globalLoadPromise = null;
const scopedLoadPromises = new Map(); // Map<string, Promise>
let supportsGlobalFontFace = null;

const canUseGlobalFontFace = () => {
  if (supportsGlobalFontFace === null) {
    try {
      supportsGlobalFontFace = wx && typeof wx.canIUse === 'function' && wx.canIUse('loadFontFace.global');
    } catch (_) {
      supportsGlobalFontFace = false;
    }
  }
  return supportsGlobalFontFace;
};

const markFamilyLoadedInContext = (family, contextId) => {
  if (!family) return;
  if (!loadedFontContexts.has(family)) {
    loadedFontContexts.set(family, new Set());
  }
  loadedFontContexts.get(family).add(contextId);
};

const hasFamilyLoadedInContext = (family, contextId) => {
  const contextSet = loadedFontContexts.get(family);
  return contextSet ? contextSet.has(contextId) : false;
};

const deriveContextId = (preferredContextId) => {
  if (preferredContextId) return preferredContextId;
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : [];
    if (!pages.length) return 'context:unknown';
    const currentPage = pages[pages.length - 1] || {};
    const route = currentPage.route || currentPage.__route__ || 'unknown';
    const webviewId = (currentPage.__wxWebviewId__ !== undefined ? currentPage.__wxWebviewId__ : (currentPage.__wxExparserNodeId__ !== undefined ? currentPage.__wxExparserNodeId__ : '0'));
    return `page:${route}#${webviewId}`;
  } catch (_) {
    return 'context:unknown';
  }
};

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

const loadSingleFont = async (fontMeta, contextId, useGlobal) => {
  const effectiveContext = useGlobal ? GLOBAL_CONTEXT_ID : contextId;

  if (hasFamilyLoadedInContext(fontMeta.family, effectiveContext)) {
    return { font: fontMeta.family, status: 'cached' };
  }

  const baseUrl = normalizeBaseUrl(envConfig.AI_AGENT_PUBLIC_URL || 'http://localhost:8080');
  const fontUrl = `${baseUrl}/resources/font/${encodeURIComponent(fontMeta.file)}`;

  try {
    const cachedPath = await resourceCache.getCachedResourceUrl(fontUrl);
    const fontSource = await buildFontSource(cachedPath, fontUrl);

    await new Promise((resolve, reject) => {
      const fontFaceOptions = {
        family: fontMeta.family,
        source: fontSource,
        desc: { style: 'normal', weight: fontMeta.weight || '400' },
        success: (res) => {
          markFamilyLoadedInContext(fontMeta.family, effectiveContext);
          envConfig.log(`✅ 挂件字体 ${fontMeta.family} 加载成功`, { status: res.status, context: effectiveContext });
          resolve(res);
        },
        fail: (err) => {
          envConfig.error(`❌ 挂件字体 ${fontMeta.family} 加载失败`, err);
          reject(err);
        }
      };

      if (useGlobal) {
        fontFaceOptions.global = true;
      } else {
        fontFaceOptions.global = false;
        fontFaceOptions.scopes = ['webview', 'native'];
      }

      wx.loadFontFace(fontFaceOptions);
    });

    return { font: fontMeta.family, status: 'loaded' };
  } catch (error) {
    envConfig.warn(`⚠️ 挂件字体 ${fontMeta.family} 加载过程中出现问题，将回退系统字体`, error);
    return { font: fontMeta.family, status: 'failed', error };
  }
};

const loadFontSet = async (contextId, useGlobal) => {
  const results = await Promise.all(CHARM_FONT_MANIFEST.map((fontMeta) => loadSingleFont(fontMeta, contextId, useGlobal)));
  const hasFailure = results.some(result => result.status === 'failed');

  if (hasFailure) {
    if (useGlobal) {
      globalLoadPromise = null;
    } else {
      scopedLoadPromises.delete(contextId);
    }
  }

  return results;
};

const loadCharmFontsOnce = (options = {}) => {
  const prefersGlobal = canUseGlobalFontFace();

  if (prefersGlobal) {
    if (!globalLoadPromise) {
      globalLoadPromise = loadFontSet(GLOBAL_CONTEXT_ID, true).catch((error) => {
        globalLoadPromise = null;
        throw error;
      });
    }
    return globalLoadPromise;
  }

  const contextId = deriveContextId(options.scopeId);

  if (!scopedLoadPromises.has(contextId)) {
    const scopedPromise = loadFontSet(contextId, false).catch((error) => {
      scopedLoadPromises.delete(contextId);
      throw error;
    });
    scopedLoadPromises.set(contextId, scopedPromise);
  }

  return scopedLoadPromises.get(contextId);
};

module.exports = {
  loadCharmFontsOnce,
  CHARM_FONT_MANIFEST
};
