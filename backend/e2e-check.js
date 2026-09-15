const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')
const XLSX = require('xlsx')

const PORT = Number(process.env.PORT || 5100)
const BASE_URL = `http://127.0.0.1:${PORT}`
const EMAIL = process.env.MORVA_LOCAL_ADMIN_EMAIL
const PASSWORD = process.env.MORVA_LOCAL_ADMIN_PASSWORD
const DATA_FILE = path.join(__dirname, 'data', 'imports.json')

if (!EMAIL || !PASSWORD) {
  throw new Error('MORVA_LOCAL_ADMIN_EMAIL and MORVA_LOCAL_ADMIN_PASSWORD must be configured for e2e checks.')
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function waitForHealth(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BASE_URL}/health`)
      if (response.ok) return
    } catch (_error) {
      // The child process may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('Backend did not become healthy within the timeout.')
}

async function expectJson(response, status, label) {
  const body = await response.json()
  assert(response.status === status, `${label}: expected HTTP ${status}, got ${response.status}`)
  return body
}

async function main() {
  const server = spawn(process.execPath, ['index.js'], {
    cwd: __dirname,
    env: { ...process.env, PORT: String(PORT) },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  let stderr = ''
  server.stderr.on('data', (chunk) => { stderr += chunk.toString() })

  try {
    await waitForHealth()

    const health = await expectJson(await fetch(`${BASE_URL}/health`), 200, 'health')
    assert(health.success === true && health.data?.mode === 'local', 'health: unexpected payload')

    const unauthorized = await expectJson(await fetch(`${BASE_URL}/imports/summary`), 401, 'unauthorized summary')
    assert(unauthorized.success === false, 'unauthorized summary: expected failure payload')

    const badLogin = await expectJson(await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: EMAIL, password: `${PASSWORD}-wrong` })
    }), 401, 'bad login')
    assert(badLogin.success === false, 'bad login: expected failure payload')

    const login = await expectJson(await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: EMAIL, password: PASSWORD })
    }), 200, 'login')
    assert(login.success === true, 'login: expected success')
    assert(typeof login.data?.accessToken === 'string' && login.data.accessToken.length > 20, 'login: access token missing')
    assert(login.data?.refreshToken === null, 'login: expected null refresh token for local backend')

    const token = login.data.accessToken
    const summary = await expectJson(await fetch(`${BASE_URL}/imports/summary`, {
      headers: { authorization: `Bearer ${token}` }
    }), 200, 'authorized summary')
    assert(summary.success === true && summary.data?.categories, 'authorized summary: unexpected payload')

    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.aoa_to_sheet([
      ['شناسه', 'نام'],
      ['E2E-001', 'کاربر آزمایشی']
    ])
    XLSX.utils.book_append_sheet(workbook, worksheet, 'پرسنل')
    const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' })

    const form = new FormData()
    form.append('file', new Blob([buffer]), 'لیست پرسنل.xlsx')
    const upload = await expectJson(await fetch(`${BASE_URL}/imports/upload`, {
      method: 'POST',
      headers: { authorization: `Bearer ${token}` },
      body: form
    }), 200, 'authorized upload')
    assert(upload.success === true, 'authorized upload: expected success')
    assert(upload.data?.imported?.recordCount === 1, 'authorized upload: expected one imported row')

    const afterUpload = await expectJson(await fetch(`${BASE_URL}/imports/summary`, {
      headers: { authorization: `Bearer ${token}` }
    }), 200, 'summary after upload')
    assert(afterUpload.data?.totals?.employees === 1, 'summary after upload: expected one employee row')

    console.log('Local backend end-to-end checks passed.')
  } finally {
    server.kill('SIGTERM')
    try {
      fs.unlinkSync(DATA_FILE)
    } catch (_error) {
      // The data file may not exist in a clean checkout.
    }
    if (stderr.trim()) process.stderr.write(stderr)
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exitCode = 1
})
