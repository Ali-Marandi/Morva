# Morva Payroll Component Coverage — 1405-05

This report is derived from the privacy-safe payroll import bundle supplied for Morva validation. Raw identifiers are not included.

## Earnings component coverage

All 27 observed earnings columns occur with a non-zero value in at least one payroll row.

| Source component | Employees with non-zero value |
|---|---:|
| حق شغل-1 | 3,256 |
| حق شاغل-2 | 3,240 |
| ترمیم حقوق-19-19 | 3,240 |
| فوق العاده خاص-129 | 3,240 |
| فوق العاده بدی آب و هوا-7 | 2,948 |
| فوق العاده شغل-22 | 2,933 |
| فوق العاده سختی کار-4 | 2,913 |
| فوق العاده رتبه بندی-18 | 2,792 |
| فوق العاده ویژه-66 | 2,791 |
| بازگشت بیمه تکمیلی-160 | 2,193 |
| تفاوت بند(ی) تبصره (12) ق.ج-95 | 1,625 |
| تفاوت جزء(1) بند(الف)تبصره(12) ق. ج-96 | 1,620 |
| تفاوت تطبیق موضوع جزء(2-1)بندالف تبصره15 ق ب 1403-50 | 1,366 |
| کمک هزینه عائله مندی-11 | 1,271 |
| کمک هزینه اولاد-12 | 992 |

Additional lower-frequency source components remain part of the 27-column canonical catalog and are required for exact replay even where their population frequency is small.

## Deduction component coverage

All 10 observed payroll deduction columns occur with a non-zero value in at least one payroll row.

| Source component | Employees with non-zero value |
|---|---:|
| بیمه عمر سهم کارمند-947 | 3,240 |
| بیمه تکمیلی درمانی-934 | 2,209 |
| بیمه خدمات درمانی(سرانه)-945 | 2,130 |
| صندوق بازنشستگی-941 | 2,004 |
| بیمه تامین اجتماعی-943 | 1,091 |
| بیمه خدمات درمانی (خاص)-946 | 173 |
| مالیات-965 | 168 |
| مقرری-942 | 37 |
| بیمه سوانح سهم کارمند-937 | 16 |
| مقرری جانباز-912 | 1 |

## Interpretation

These counts describe the supplied source population only. They do not, by themselves, establish legal eligibility or tax/pension/insurance treatment. Legal behavior must come from an approved, versioned Morva Rule Pack.

## Golden invariant

For every source payroll row in the supplied population:

- sum of the 27 earnings components equals `جمع مزایا` exactly;
- `جمع مزایا - جمع کسور` equals `خالص پرداختی` exactly.
