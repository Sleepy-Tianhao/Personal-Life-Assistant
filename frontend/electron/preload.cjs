const { contextBridge, ipcRenderer } = require('electron')

function subscribe(channel, callback) {
  const listener = (_event, payload) => callback(payload)
  ipcRenderer.on(channel, listener)
  return () => ipcRenderer.removeListener(channel, listener)
}

contextBridge.exposeInMainWorld('desktop', {
  platform: process.platform,
  minimize: () => ipcRenderer.invoke('window:minimize'),
  toggleMaximize: () => ipcRenderer.invoke('window:toggle-maximize'),
  isMaximized: () => ipcRenderer.invoke('window:is-maximized'),
  close: () => ipcRenderer.invoke('window:close'),
  onMaximizedChange: (callback) => {
    const listener = (_event, maximized) => callback(Boolean(maximized))
    ipcRenderer.on('window:maximized-changed', listener)
    return () => ipcRenderer.removeListener('window:maximized-changed', listener)
  },
  floating: {
    getState: () => ipcRenderer.invoke('floating:get-state'),
    setEnabled: (enabled) => ipcRenderer.invoke('floating:set-enabled', Boolean(enabled)),
    updateBlocks: (blocks) => ipcRenderer.invoke('floating:update-blocks', blocks),
    setLocked: (locked) => ipcRenderer.invoke('floating:set-locked', Boolean(locked)),
    resize: (size) => ipcRenderer.send('floating:resize', size),
    openMain: () => ipcRenderer.invoke('app:show-main'),
    hide: () => ipcRenderer.invoke('floating:set-enabled', false),
    onStateChanged: (callback) => subscribe('floating:state-changed', callback),
    onConfigChanged: (callback) => subscribe('floating:config-changed', callback),
  },
})
