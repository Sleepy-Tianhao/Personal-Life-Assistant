import { chromium } from 'playwright'

const baseUrl = process.env.APP_URL || 'http://127.0.0.1:5173'
const routes = [
  ['今日', '/#/'],
  ['待办', '/#/todos'],
  ['日程', '/#/schedule'],
  ['课表', '/#/timetable'],
  ['账本', '/#/ledger'],
  ['日记', '/#/diary'],
  ['设置', '/#/settings'],
]

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const issues = []

page.on('console', (message) => {
  if (message.type() === 'error' || message.type() === 'warning') {
    issues.push(`[console:${message.type()}] ${message.text()}`)
  }
})
page.on('pageerror', (error) => {
  issues.push(`[pageerror] ${error.message}`)
})

for (const [name, path] of routes) {
  const before = issues.length
  const response = await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(700)
  // Hash navigation resolves as a same-document navigation and may return null.
  if (response && !response.ok()) {
    issues.push(`[navigation] ${name} returned ${response.status()}`)
  }
  const current = issues.length - before
  console.log(`${current ? 'FAIL' : 'OK  '} ${name.padEnd(4)} ${path}`)
}

const floatingBefore = issues.length
await page.goto(`${baseUrl}/floating.html`, { waitUntil: 'networkidle' })
await page.waitForTimeout(900)
const floatingWidgetCount = await page.locator('.floating-widget').count()
if (floatingWidgetCount < 1) {
  issues.push('[floating] no floating widgets rendered')
}
console.log(
  `${issues.length > floatingBefore ? 'FAIL' : 'OK  '} 浮窗 ${floatingWidgetCount} 个板块`,
)

await browser.close()

if (issues.length) {
  console.error(`\n${issues.length} frontend issue(s) found:`)
  for (const issue of issues) console.error(`- ${issue}`)
  process.exit(1)
}

console.log('\nUI smoke test passed with no console errors.')
