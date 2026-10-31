const fs = require('node:fs')
const path = require('node:path')

const { app, BrowserWindow, ipcMain, screen, shell } = require('electron')

let mainWindow = null
let floatingWindow = null
let floatingConfig = null
let configPath = null
let savePositionTimer = null
let floatingHasBeenSized = false
let closingFloatingForApp = false
let isQuitting = false

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL)
const MAX_FLOATING_BLOCKS = 8
const ALLOWED_BLOCK_TYPES = new Set([
  'clock',
  'date',
  'currentCourse',
  'todayCourses',
  'pendingTodos',
  'nextSchedule',
  'monthlyFinance',
  'diaryStatus',
  'custom',
])

const DEFAULT_BLOCKS = [
  { id: 'default-clock', type: 'clock', text: '' },
  { id: 'default-date', type: 'date', text: '' },
  { id: 'default-course', type: 'currentCourse', text: '' },
  { id: 'default-todos', type: 'pendingTodos', text: '' },
]

if (process.platform === 'linux') {
  app.commandLine.appendSwitch('enable-transparent-visuals')
}

function sendMaximizedState() {
  if (!mainWindow || mainWindow.isDestroyed()) return
  mainWindow.webContents.send('window:maximized-changed', mainWindow.isMaximized())
}

function normalizeFloatingBlocks(blocks) {
  if (!Array.isArray(blocks) || !blocks.length) {
    return DEFAULT_BLOCKS.map((block) => ({ ...block }))
  }

  const usedIds = new Set()
  const result = []

  blocks.slice(0, MAX_FLOATING_BLOCKS).forEach((block, index) => {
    if (!block || !ALLOWED_BLOCK_TYPES.has(block.type)) return
    let id = String(block.id || `block-${index}`).slice(0, 80)
    while (usedIds.has(id)) id = `${id}-${index}`
    usedIds.add(id)
    result.push({
      id,
      type: block.type,
      text: block.type === 'custom' ? String(block.text || '').slice(0, 80) : '',
    })
  })

  return result.length ? result : DEFAULT_BLOCKS.map((block) => ({ ...block }))
}

function normalizePosition(position) {
  if (!position) return null
  const x = Number(position.x)
  const y = Number(position.y)
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null
  return { x: Math.round(x), y: Math.round(y) }
}

function defaultConfig() {
  return {
    version: 1,
    enabled: false,
    locked: false,
    blocks: DEFAULT_BLOCKS.map((block) => ({ ...block })),
    position: null,
  }
}

function loadFloatingConfig() {
  try {
    const raw = JSON.parse(fs.readFileSync(configPath, 'utf8'))
    return {
      version: 1,
      enabled: Boolean(raw.enabled),
      locked: Boolean(raw.locked),
      blocks: normalizeFloatingBlocks(raw.blocks),
      position: normalizePosition(raw.position),
    }
  } catch {
    return defaultConfig()
  }
}

function persistFloatingConfig() {
  if (!configPath || !floatingConfig) return
  try {
    fs.mkdirSync(path.dirname(configPath), { recursive: true })
    const temporaryPath = `${configPath}.tmp`
    fs.writeFileSync(temporaryPath, `${JSON.stringify(floatingConfig, null, 2)}\n`, 'utf8')
    fs.renameSync(temporaryPath, configPath)
  } catch (error) {
    console.error('Unable to save floating board configuration:', error)
  }
}

function getFloatingState() {
  return {
    available: true,
    enabled: floatingConfig?.enabled ?? false,
    visible: Boolean(floatingWindow && !floatingWindow.isDestroyed() && floatingWindow.isVisible()),
    locked: floatingConfig?.locked ?? false,
    blocks: (floatingConfig?.blocks || DEFAULT_BLOCKS).map((block) => ({ ...block })),
  }
}

function notifyMainState() {
  if (!mainWindow || mainWindow.isDestroyed()) return
  mainWindow.webContents.send('floating:state-changed', getFloatingState())
}

function broadcastFloatingConfig() {
  if (!floatingWindow || floatingWindow.isDestroyed()) return
  floatingWindow.webContents.send('floating:config-changed', getFloatingState())
}

function isPositionOnScreen(position) {
  if (!position) return false
  return screen.getAllDisplays().some((display) => {
    const area = display.workArea
    return (
      position.x >= area.x - 40 &&
      position.x < area.x + area.width - 80 &&
      position.y >= area.y - 20 &&
      position.y < area.y + area.height - 40
    )
  })
}

function initialFloatingPosition(width, height) {
  const saved = floatingConfig?.position
  if (isPositionOnScreen(saved)) return saved
  const area = screen.getPrimaryDisplay().workArea
  return {
    x: Math.round(area.x + (area.width - width) / 2),
    y: area.y + 18,
  }
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum)
}

function schedulePositionSave() {
  if (!floatingWindow || floatingWindow.isDestroyed() || !floatingConfig) return
  if (savePositionTimer) clearTimeout(savePositionTimer)
  savePositionTimer = setTimeout(() => {
    if (!floatingWindow || floatingWindow.isDestroyed()) return
    const [x, y] = floatingWindow.getPosition()
    floatingConfig.position = { x, y }
    persistFloatingConfig()
  }, 350)
}

function floatingPageUrl() {
  return `${String(process.env.VITE_DEV_SERVER_URL).replace(/\/+$/, '')}/floating.html`
}

function loadFloatingPage(window) {
  if (isDev) {
    window.loadURL(floatingPageUrl())
  } else {
    window.loadFile(path.join(__dirname, '..', 'dist', 'floating.html'))
  }
}

function createFloatingWindow() {
  if (floatingWindow && !floatingWindow.isDestroyed()) {
    if (floatingConfig.enabled && !floatingWindow.isVisible()) {
      floatingWindow.showInactive()
    }
    return floatingWindow
  }

  const width = 900
  const height = 64
  const position = initialFloatingPosition(width, height)
  floatingHasBeenSized = false
  closingFloatingForApp = false

  floatingWindow = new BrowserWindow({
    width,
    height,
    x: position.x,
    y: position.y,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    hasShadow: false,
    resizable: false,
    movable: true,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    focusable: true,
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  floatingWindow.setAlwaysOnTop(true)
  floatingWindow.setSkipTaskbar(true)
  floatingWindow.setMenuBarVisibility(false)

  if (process.platform !== 'win32') {
    try {
      floatingWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
    } catch {
      // Some Linux window managers do not support workspace pinning.
    }
  }

  floatingWindow.on('moved', schedulePositionSave)

  floatingWindow.once('ready-to-show', () => {
    if (!floatingWindow || floatingWindow.isDestroyed()) return
    if (floatingConfig.enabled) floatingWindow.showInactive()
    notifyMainState()
  })

  floatingWindow.webContents.on('did-finish-load', () => {
    broadcastFloatingConfig()
    notifyMainState()
  })

  floatingWindow.on('closed', () => {
    floatingWindow = null
    if (!closingFloatingForApp && !isQuitting && floatingConfig?.enabled) {
      floatingConfig.enabled = false
      persistFloatingConfig()
      notifyMainState()
    }
  })

  loadFloatingPage(floatingWindow)
  return floatingWindow
}

function setFloatingEnabled(enabled) {
  const nextEnabled = Boolean(enabled)
  floatingConfig.enabled = nextEnabled
  persistFloatingConfig()

  if (nextEnabled) {
    const existing = floatingWindow && !floatingWindow.isDestroyed()
    const window = createFloatingWindow()
    if (existing && !window.isVisible()) window.showInactive()
  } else if (floatingWindow && !floatingWindow.isDestroyed()) {
    floatingWindow.hide()
  }

  const state = getFloatingState()
  notifyMainState()
  broadcastFloatingConfig()
  return state
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

function destroyFloatingForApp() {
  if (!floatingWindow || floatingWindow.isDestroyed()) return
  closingFloatingForApp = true
  floatingWindow.destroy()
  floatingWindow = null
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1040,
    minHeight: 680,
    show: false,
    frame: false,
    backgroundColor: '#f3f8f2',
    roundedCorners: true,
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (isDev) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    setTimeout(notifyMainState, 300)
  })

  mainWindow.on('maximize', sendMaximizedState)
  mainWindow.on('unmaximize', sendMaximizedState)

  mainWindow.on('closed', () => {
    mainWindow = null
    destroyFloatingForApp()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })
}

ipcMain.handle('window:minimize', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.minimize()
})

ipcMain.handle('window:toggle-maximize', (event) => {
  const window = BrowserWindow.fromWebContents(event.sender)
  if (!window) return false
  if (window.isMaximized()) {
    window.unmaximize()
  } else {
    window.maximize()
  }
  return window.isMaximized()
})

ipcMain.handle('window:is-maximized', (event) => {
  return BrowserWindow.fromWebContents(event.sender)?.isMaximized() ?? false
})

ipcMain.handle('window:close', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.close()
})

ipcMain.handle('floating:get-state', () => getFloatingState())

ipcMain.handle('floating:set-enabled', (_event, enabled) => {
  return setFloatingEnabled(enabled)
})

ipcMain.handle('floating:update-blocks', (_event, blocks) => {
  floatingConfig.blocks = normalizeFloatingBlocks(blocks)
  persistFloatingConfig()
  broadcastFloatingConfig()
  notifyMainState()
  return getFloatingState()
})

ipcMain.handle('floating:set-locked', (_event, locked) => {
  floatingConfig.locked = Boolean(locked)
  persistFloatingConfig()
  broadcastFloatingConfig()
  notifyMainState()
  return getFloatingState()
})

ipcMain.handle('app:show-main', () => {
  showMainWindow()
})

ipcMain.on('floating:resize', (event, size) => {
  if (!floatingWindow || floatingWindow.isDestroyed()) return
  if (event.sender !== floatingWindow.webContents) return

  const requestedWidth = Number(size?.width)
  const requestedHeight = Number(size?.height)
  if (!Number.isFinite(requestedWidth) || !Number.isFinite(requestedHeight)) return

  const bounds = floatingWindow.getBounds()
  const display = screen.getDisplayMatching(bounds)
  const area = display.workArea
  const width = clamp(Math.ceil(requestedWidth), 300, Math.max(300, area.width - 16))
  const height = clamp(Math.ceil(requestedHeight), 48, 220)

  let x = bounds.x
  if (!floatingHasBeenSized && !isPositionOnScreen(floatingConfig.position)) {
    x = Math.round(area.x + (area.width - width) / 2)
  } else {
    x = clamp(bounds.x, area.x, area.x + Math.max(0, area.width - width))
  }
  const y = clamp(bounds.y, area.y, area.y + Math.max(0, area.height - height))

  floatingHasBeenSized = true
  floatingWindow.setBounds({ x, y, width, height }, false)
})

app.whenReady().then(() => {
  app.setName('Life Assistant')
  if (process.platform === 'win32') {
    app.setAppUserModelId('tech.personal.lifeassistant')
  }

  configPath = path.join(app.getPath('userData'), 'floating-board.json')
  floatingConfig = loadFloatingConfig()

  createWindow()
  if (floatingConfig.enabled) {
    createFloatingWindow()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
      if (floatingConfig.enabled) createFloatingWindow()
    }
  })
})

app.on('before-quit', () => {
  isQuitting = true
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
