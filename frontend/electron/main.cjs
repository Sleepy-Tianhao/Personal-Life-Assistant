const path = require('node:path')

const { app, BrowserWindow, ipcMain, shell } = require('electron')

let mainWindow = null

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL)

function sendMaximizedState() {
  if (!mainWindow || mainWindow.isDestroyed()) return
  mainWindow.webContents.send('window:maximized-changed', mainWindow.isMaximized())
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1040,
    minHeight: 680,
    show: false,
    frame: false,
    backgroundColor: '#070a0f',
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
  })

  mainWindow.on('maximize', sendMaximizedState)
  mainWindow.on('unmaximize', sendMaximizedState)

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

app.whenReady().then(() => {
  app.setName('Life Assistant')
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
