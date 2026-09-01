# Morva Payroll Dictionary

هدف این فرهنگ، استانداردکردن واژگان مالی است. `code`‌ها پایدار هستند؛ عنوان فارسی می‌تواند بدون شکستن API تغییر کند.

## Earnings

| Code | عنوان |
|---|---|
| BASE_SALARY | حقوق پایه/مبنای حکم |
| JOB_RIGHT | حق شغل |
| INCUMBENT_RIGHT | حق شاغل |
| JOB_ALLOWANCE | فوق‌العاده شغل |
| RANK_ALLOWANCE | فوق‌العاده رتبه‌بندی |
| SPECIAL_ALLOWANCE | فوق‌العاده ویژه |
| MANAGEMENT_ALLOWANCE | فوق‌العاده مدیریت/سرپرستی |
| REGION_ALLOWANCE | فوق‌العاده شرایط/منطقه خدمت |
| WEATHER_ALLOWANCE | فوق‌العاده بدی آب‌وهوا، در صورت احراز |
| OVERTIME | اضافه‌کار |
| TEACHING_FEE | حق‌التدریس |
| MISSION | فوق‌العاده/هزینه مأموریت |
| FAMILY_ALLOWANCE | عائله‌مندی |
| CHILD_ALLOWANCE | اولاد |
| OTHER_EARNING | سایر پرداخت‌های مجاز |

## Deductions

| Code | عنوان |
|---|---|
| TAX | مالیات حقوق |
| PENSION | کسور بازنشستگی |
| INSURANCE | بیمه |
| MEDICAL | درمان |
| LOAN | اقساط وام |
| DEBT | بدهی/مطالبات |
| ADVANCE | مساعده |
| COURT_ORDER | کسر بابت حکم قضایی |
| OTHER_DEDUCTION | سایر کسورات مجاز |

## ویژگی‌های هر قلم

هر قلم باید تعیین کند:

- taxable
- pensionable
- insurable
- fixed_salary
- overtime_base
- minimum_pay_base
- rank_base
- retirement_base
- eligibility_rule
- calculation_rule
- minimum / maximum
- legal_reference

تا تعیین وضعیت قانونی یک قلم، مقدار پیش‌فرض آن در Rule Pack تولیدی `review_required` است.
