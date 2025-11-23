// eslint-disable-next-line import/no-extraneous-dependencies
import { MetaTag, Tag } from '@kibalabs/build/scripts/plugins/injectSeoPlugin.js';

const title = 'Range Seeker';
const description = 'AI Agents for Uniswap V3 LP Optimization';
const url = 'https://rangeseeker.xyz';
const imageUrl = `${url}/assets/banner.png`;

const farcasterFrameJson = JSON.stringify({
  version: 'next',
  imageUrl: `${url}/assets/farcaster-frame/image.png`,
  button: {
    title: 'Launch',
    action: {
      type: 'launch_frame',
      name: title,
      url,
      splashImageUrl: `${url}/assets/farcaster-frame/splash.png`,
      splashBackgroundColor: '#000000',
    },
  },
});

const seoTags = [
  new MetaTag('description', description),
  new Tag('meta', { property: 'og:title', content: title }),
  new Tag('meta', { property: 'og:description', content: description }),
  new Tag('meta', { property: 'og:url', content: url }),
  new Tag('meta', { property: 'og:image', content: imageUrl }),
  new MetaTag('twitter:card', 'summary_large_image'),
  new MetaTag('twitter:site', '@tokenpagexyz'),
  new Tag('link', { rel: 'canonical', href: url }),
  new Tag('link', { rel: 'icon', type: 'image/png', href: '/assets/icon.png' }),
  new MetaTag('fc:frame', farcasterFrameJson),
];

export default (config) => {
  const newConfig = config;
  newConfig.seoTags = seoTags;
  newConfig.title = title;
  newConfig.analyzeBundle = false;
  newConfig.viteConfigModifier = (viteConfig) => {
    const newViteConfig = viteConfig;
    // Listen everywhere
    newViteConfig.server.host = '0.0.0.0';
    newViteConfig.server.allowedHosts = true;
    return newViteConfig;
  };
  return newConfig;
};
