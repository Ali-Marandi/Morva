const fs = require('fs')
const path = require('path')

const source = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8')

const forbiddenPatterns = [
  /const\s+ADMIN_ACCOUNT\s*=/,
  /mock-access-token/,
  /mock-refresh-token/,
  /app\.use\(cors\(\)\)/
]

for (const pattern of forbiddenPatterns) {
  if (pattern.test(source)) {
    throw new Error(`Backend security regression detected: ${pattern}`)
  }
}

const requiredPatterns = [
  /MORVA_LOCAL_ADMIN_EMAIL/,
  /MORVA_LOCAL_ADMIN_PASSWORD/,
  /MORVA_LOCAL_CORS_ORIGIN/,
  /crypto\.randomBytes\(/,
  /function requireAuth\(/,
  /app\.get\('\/health'/,
  /app\.get\('\/imports\/summary', requireAuth/,
  /app\.post\('\/imports\/upload', requireAuth/
]

for (const pattern of requiredPatterns) {
  if (!pattern.test(source)) {
    throw new Error(`Backend security requirement missing: ${pattern}`)
  }
}

console.log('Local backend security checks passed.')
