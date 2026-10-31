# Personal Life Assistant — Desktop Frontend

Vue 3 + Vite + Electron 前端，对应本地 FastAPI + SQLite 后端。

## 界面设计研究

设计语言参考了 [ClassIsland](https://github.com/ClassIsland/ClassIsland) 的 Fluent 桌面界面：

- Windows 11 Fluent / Mica 式深色半透明材质；
- 左侧 NavigationView 导航与大面积内容卡片；
- 顶部居中的悬浮胶囊信息岛；
- 明亮蓝色强调色、小圆角控件、紧凑的信息层级；
- 课程条、状态条与周视图的组合方式。

本项目没有复制 ClassIsland 的代码或素材，所有组件、布局、文案、颜色和品牌图标均为独立实现，并根据个人生活助理的使用场景重新设计了信息架构。

## 已实现页面

| 页面 | 能力 |
| --- | --- |
| 今日 | 顶栏实时信息岛、今日课程/日程时间轴、待办焦点、本月收支、最近日记 |
| 待办 | 状态/优先级筛选、搜索、新建、编辑、完成、删除 |
| 日程 | 周一至周日日历、全天日程、重叠事件分栏、周切换、新建/编辑/删除 |
| 课表 | HTML 导入、拖拽上传、学期起始日、周次计算、课程色块、当前课程高亮、课表切换/激活、删除 |
| 账本 | 月度收支汇总、分类占比、按日流水、类型筛选、新建/编辑/删除 |
| 日记 | 搜索、日期列表、心情/天气、正文编辑、未保存提示、`Ctrl/Cmd + S` 保存、删除 |
| 设置 | 后端连接、服务状态、API 地址、强调色、文档链接、隐私与版本信息 |

## 技术栈

- Vue 3（Composition API）
- Vue Router
- Pinia
- Vite
- Electron
- `@lucide/vue` 图标
- 纯 CSS 设计系统（无 UI 组件库）

## 环境要求

- Node.js 22.12+
- npm
- 已运行的 FastAPI 后端

## 启动

先启动后端：

```bash
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

再启动前端：

```bash
cd frontend
npm install
npm run dev          # 浏览器开发模式，http://127.0.0.1:5173
npm run dev:desktop  # Electron 开发模式
```

Electron 开发模式会等待 Vite 启动后再打开桌面窗口。

## API 地址

默认地址为 `http://127.0.0.1:8000/api/v1`，可在设置页修改，保存在浏览器/Electron 的 localStorage 中。

也可以在 `.env` 中覆盖：

```bash
cp .env.example .env
```

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

后端的 CORS 默认允许：

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `null`（Electron 打包后通过 `file://` 加载页面时的 Origin）

## 构建与打包

```bash
npm run build      # 构建 Vite 静态资源
npm run desktop    # 用 Electron 加载 dist/index.html（需要后端已启动）
npm run dist       # 生成 Electron 安装包
```

`electron-builder` 配置了 Windows NSIS、macOS DMG、Linux AppImage/deb 目标。通常应在对应操作系统上构建对应安装包。

当前安装包只包含 Electron 前端壳，Python 后端需要单独启动。若要把后端也打进桌面应用，下一步应使用 PyInstaller 生成单文件后端，并在 Electron 主进程启动/退出时管理该子进程。

## 目录结构

```text
frontend/
├── electron/
│   ├── main.cjs            # BrowserWindow、IPC 窗口控制、外链处理
│   └── preload.cjs         # 安全的 window.desktop 桥接
├── public/
│   └── brand-mark.svg
├── build/
│   └── icon.png            # 桌面应用图标
├── src/
│   ├── api/                # fetch 客户端与后端资源封装
│   ├── components/         # 标题栏、信息岛、导航、Modal、Toast 等
│   ├── stores/             # Pinia：应用状态、Toast、确认对话框
│   ├── styles/             # 设计 tokens 与全局样式
│   ├── utils/              # 日期、金额、颜色、主题
│   ├── views/              # 七个页面
│   ├── App.vue
│   ├── main.js
│   └── router.js
└── vite.config.js
```

## 设计系统

- 背景：深色蓝黑 Mica 氛围，低对比网格与径向光晕。
- 组件：玻璃卡片 + 细描边 + 柔和阴影。
- 强调色：默认 `#59C2FF`，可选薄荷青、暮光紫、晚霞粉、暖阳金。
- 字体：Segoe UI Variable / Noto Sans SC / 系统字体回退。
- 圆角：7 / 10 / 14 / 20 / 28px。
- 动画：180–240ms 的轻量淡入、位移与弹性缩放。

## 测试

前端冒烟测试会遍历全部页面并检查控制台错误和 Vue 警告：

```bash
npx playwright install chromium
npm run test:ui
```

测试要求 Vite 开发服务器和后端均已启动。可通过 `APP_URL` 覆盖前端地址。

## 验证状态

- `npm run build` 通过。
- 所有页面在 Chromium 中无控制台错误或 Vue 警告。
- Electron 开发模式和生产构建的 `file://` 加载均已验证，CORS 与 `window.desktop` 桥接正常。
- Linux 的 `electron-builder --dir` 解包产物已验证可启动并连接后端。
- 新建待办、新建账目、新建日程、编辑并保存日记、课程表加载、强调色切换已验证。

## 已知边界

- 不自动启动/打包 Python 后端。
- 不支持浅色主题。
- 课表仅支持 HTML 导入，不支持手工编辑课程。
- 没有离线缓存；后端未启动时会显示连接错误。
- 暂未实现系统托盘、课程提醒和桌面通知。
