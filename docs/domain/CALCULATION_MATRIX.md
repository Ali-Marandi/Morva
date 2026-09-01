# Morva Calculation Matrix

این ماتریس قرارداد بین قلم، شرط احراز، مبنا و آثار مالی است. `review_required` یعنی قبل از production باید توسط کارشناس و متن منبع اولیه تأیید شود.

| Component | Basis | Eligibility | Tax | Pension | Insurance | Payroll impact |
|---|---|---|---|---|---|---|
| JOB_RIGHT | امتیاز/ضریب شغل | طبق شغل و حکم | review_required | review_required | review_required | earning |
| INCUMBENT_RIGHT | امتیاز/ضریب شاغل | طبق سابقه/شایستگی و حکم | review_required | review_required | review_required | earning |
| JOB_ALLOWANCE | مبنای قانونی مربوط | طبق شغل | review_required | review_required | review_required | earning |
| RANK_ALLOWANCE | مبنای رتبه‌بندی | رتبه معتبر + شرایط | review_required | review_required | review_required | earning |
| FAMILY_ALLOWANCE | سیاست عائله‌مندی | dependent eligibility | review_required | review_required | review_required | earning |
| CHILD_ALLOWANCE | سیاست اولاد | dependent eligibility | review_required | review_required | review_required | earning |
| OVERTIME | ساعت/نرخ مصوب | attendance + authorization | review_required | review_required | review_required | earning |
| TEACHING_FEE | ساعات تدریس | assignment + approval | review_required | review_required | review_required | earning |
| TAX | taxable income | tax profile | deduction | n/a | n/a | deduction |
| PENSION | pensionable base | pension profile | deduction | deduction | n/a | deduction |
| INSURANCE | insurable base | insurance profile | deduction | n/a | deduction | deduction |
| LOAN | amortization schedule | active loan | n/a | n/a | n/a | deduction |
| COURT_ORDER | حکم قضایی | valid order | review_required | review_required | review_required | deduction |

## Mandatory rule metadata

هر سطر اجرایی باید علاوه بر این جدول، `legal_reference`, `effective_from`, `effective_to`, `rule_version`, `review_status` و `regression_case_ids` داشته باشد.

## Invariant

هیچ Rule صرفاً به دلیل شباهت نام قلم با نرم‌افزارهای قبلی فعال نمی‌شود. Activation نیازمند منبع و تست است.
