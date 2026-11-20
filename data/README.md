# Data

**Source:** 84.51° *The Complete Journey*: grocery shopping by 2,469 households across 2017, from one retailer. The data is provided for research and educational purposes.

The raw tables are not committed. To get them:

```bash
pip install completejourney-py
python data/get_data.py        # copies the 8 Parquet tables into data/raw/
```

| Table | Rows | Used for |
|---|---|---|
| transactions | 1,469,307 | Every basket line: units, net sales, loyalty discount, coupon and coupon-match discounts |
| products | 92,331 | Department, category, product type, brand |
| promotions | 20,940,529 | Weekly mailer and in-store display placement by product and store (12,785 duplicate rows removed in staging) |
| campaigns / campaign_descriptions | 6,589 / 27 | Which households were in which campaign, type and dates |
| coupons / coupon_redemptions | 116,204 / 2,102 | Coupon pools and redemptions |
| demographics | 801 | Age, income and household type for some households (not used in the core analysis) |

The tables reach Python through the `completejourney-py` package (MIT licence), a port of the `completejourney` R package by Bradley Boehmke.
