# Documentation Local Deployment Guide

## Quick Start

### 1. Enter docs directory
```bash
cd docs
```

### 2. Install dependencies
```bash
npm install
# or use pnpm
pnpm install
```

### 3. Start development server
```bash
npm run dev
# or
pnpm dev
```

### 4. Access documentation
Open browser and visit: http://localhost:3000

## Project Information
- Framework: Next.js + Fumadocs
- Supported languages: Chinese(zh), English(en)
- Development port: 3000

## Common Commands
- `npm run dev` - Start development server
- `npm run build` - Build production version
- `npm run start` - Start production server

## Directory Structure
- `content/docs/` - Documentation content
- `app/` - Next.js app routing
- `components/` - React components
- `public/` - Static assets