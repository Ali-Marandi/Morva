const express = require('express')
const cors = require('cors')
const multer = require('multer')
const XLSX = require('xlsx')
const fs = require('fs')
const path = require('path')
const app = express()

app.use(cors())
app.use(express.json())

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 },
  fileFilter: (_req, file, callback) => {
    if (path.extname(file.originalname).toLowerCase() !== '.xlsx') {
      return callback(new Error('فقط فایل‌های Excel با پسوند .xlsx پذیرفته می‌شوند.'))
    }
    callback(null, true)
  }
})

const DATA_DIRECTORY = path.join(__dirname, 'data')
const DATA_FILE = path.join(DATA_DIRECTORY, 'imports.json')
fs.mkdirSync(DATA_DIRECTORY, { recursive: true })

const categories = {
  employees: 'اطلاعات پرسنل',
  payrolls: 'لیست حقوق',
  rulings: 'احکام حقوقی',
  supplementaryInsurance: 'بیمه تکمیلی',
  healthInsurance: 'بیمه خدمات درمانی',
  installments: 'کسر اقساط'
}

function readStore() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'))
  } catch (_error) {
    return { sources: {} }
  }
}

function writeStore(store) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(store), 'utf8')
}

function getCategory(fileName) {
  const name = fileName.toLowerCase()
  if (name.includes('prs info') || name.includes('لیست پرسنل')) return 'employees'
  if (name.includes('لیست حقوق')) return 'payrolls'
  if (name.includes('احکام حقوقی')) return 'rulings'
  if (name.includes('بیمه تکمیلی')) return 'supplementaryInsurance'
  if (name.includes('بیمه خدمات درمانی')) return 'healthInsurance'
  if (name.includes('کسر اقساط')) return 'installments'
  return null
}

function decodeFileName(fileName) {
  // Multer may expose non-Latin file names as Latin-1 bytes in multipart requests.
  if (/[ÃØÙ]/.test(fileName)) {
    return Buffer.from(fileName, 'latin1').toString('utf8')
  }
  return fileName
}

function importSummary(store) {
  const totals = Object.fromEntries(Object.keys(categories).map((key) => [key, 0]))
  const sources = Object.values(store.sources).map(({ rows, ...source }) => {
    totals[source.category] += rows.length
    return { ...source, recordCount: rows.length }
  })
  return { categories, totals, sources }
}

// Local development-only administrator account.
const ADMIN_ACCOUNT = {
  id: 'admin-local',
  email: 'admin@morva.local',
  password: 'Admin12345!',
  name: 'مدیر سامانه',
  role: 'admin',
  permissions: ['*']
}

app.post('/auth/login', (req, res) => {
  const { email, password } = req.body

  if (email !== ADMIN_ACCOUNT.email || password !== ADMIN_ACCOUNT.password) {
    return res.status(401).json({
      success: false,
      error: { message: 'ایمیل یا رمز عبور نادرست است.' }
    })
  }

  res.json({
    success: true,
    data: {
      accessToken: 'mock-access-token',
      refreshToken: 'mock-refresh-token',
      expiresIn: 3600,
      user: {
        id: ADMIN_ACCOUNT.id,
        email: ADMIN_ACCOUNT.email,
        name: ADMIN_ACCOUNT.name,
        role: ADMIN_ACCOUNT.role,
        permissions: ADMIN_ACCOUNT.permissions
      }
    }
  })
})

app.get('/imports/summary', (_req, res) => {
  res.json({ success: true, data: importSummary(readStore()) })
})

app.post('/imports/upload', upload.single('file'), (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: { message: 'یک فایل Excel انتخاب کنید.' } })
    }

    const fileName = decodeFileName(req.file.originalname)
    const category = getCategory(fileName)
    if (!category) {
      return res.status(400).json({
        success: false,
        error: { message: 'نام فایل شناخته نشد. یکی از گزارش‌های معرفی‌شده را انتخاب کنید.' }
      })
    }

    const workbook = XLSX.read(req.file.buffer, { type: 'buffer', cellDates: false })
    const firstSheetName = workbook.SheetNames[0]
    if (!firstSheetName) {
      return res.status(400).json({ success: false, error: { message: 'فایل هیچ شیتی ندارد.' } })
    }

    const worksheet = workbook.Sheets[firstSheetName]
    const rows = XLSX.utils.sheet_to_json(worksheet, { defval: null, raw: false })
    const headers = XLSX.utils.sheet_to_json(worksheet, { header: 1, range: 0 })[0] || []
    if (!rows.length || !headers.length) {
      return res.status(400).json({ success: false, error: { message: 'فایل دادهٔ قابل‌ورود ندارد.' } })
    }

    const store = readStore()
    const sourceKey = path.basename(fileName).toLowerCase()
    store.sources[sourceKey] = {
      sourceKey,
      fileName,
      category,
      categoryLabel: categories[category],
      sheetName: firstSheetName,
      headers,
      importedAt: new Date().toISOString(),
      rows
    }
    writeStore(store)

    res.json({
      success: true,
      data: {
        message: `${rows.length.toLocaleString('fa-IR')} ردیف با موفقیت وارد شد.`,
        imported: { fileName, category, categoryLabel: categories[category], recordCount: rows.length, headers }
      }
    })
  } catch (error) {
    next(error)
  }
})

app.use((error, _req, res, _next) => {
  if (error instanceof multer.MulterError && error.code === 'LIMIT_FILE_SIZE') {
    return res.status(400).json({ success: false, error: { message: 'حجم فایل نباید بیشتر از ۲۵ مگابایت باشد.' } })
  }
  res.status(400).json({ success: false, error: { message: error.message || 'امکان پردازش فایل وجود ندارد.' } })
})

const PORT = process.env.PORT || 5000
app.listen(PORT, () => console.log(`Backend running on http://localhost:${PORT}`))
