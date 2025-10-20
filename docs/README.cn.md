# 文档项目本地部署指南

## 快速开始

### 1. 进入文档目录
```bash
cd docs
```

### 2. 安装依赖
```bash
npm install
# 或使用 pnpm
pnpm install
```

### 3. 启动开发服务器
```bash
npm run dev
# 或
pnpm dev
```

### 4. 访问文档
打开浏览器访问：http://localhost:3000

## 项目信息
- 框架：Next.js + Fumadocs
- 支持语言：中文(zh)、英文(en)
- 开发端口：3000

## 常用命令
- `npm run dev` - 启动开发服务器
- `npm run build` - 构建生产版本
- `npm run start` - 启动生产服务器

## 目录结构
- `content/docs/` - 文档内容
- `app/` - Next.js 应用路由
- `components/` - React 组件
- `public/` - 静态资源