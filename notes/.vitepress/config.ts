import { defineConfig } from 'vitepress'

export default defineConfig({
  title: '集品笔记',
  description: 'AI 学习笔记与技术知识库',
  lang: 'zh-CN',
  base: '/ji_pin/',
  themeConfig: {
    siteTitle: '📖 集品笔记',
    logo: '/assets/logo.svg',
    nav: [
      { text: '首页', link: '/' },
      { text: 'AI 入门', link: '/ai-basics' },
      { text: '工具推荐', link: '/tools' },
      { text: 'Prompt 技巧', link: '/prompt-tips' },
      { text: '飞书机器人', link: '/feishu-bot' },
      { text: 'GitHub', link: 'https://github.com/jipin-ai/ji_pin' },
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/jipin-ai/ji_pin' }
    ],
    sidebar: {
      '/': [
        {
          text: '开始',
          items: [
            { text: '关于集品', link: '/' },
            { text: '为什么要写笔记', link: '/why' },
          ]
        },
        {
          text: 'AI 学习',
          items: [
            { text: 'AI 入门指南', link: '/ai-basics' },
            { text: 'LLM 的原理', link: '/llm-basics' },
            { text: 'Prompt 技巧', link: '/prompt-tips' },
          ]
        },
        {
          text: '实践项目',
          items: [
            { text: '飞书机器人搭建', link: '/feishu-bot' },
            { text: 'AI 工具推荐', link: '/tools' },
          ]
        }
      ]
    },
    footer: {
      message: '集品 — 收集品质好物，分享AI智慧',
      copyright: 'MIT Licensed'
    }
  }
})
