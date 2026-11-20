-- Household x campaign, with campaign start and end converted to the transaction week numbering (week 1 starts 1 Jan 2017).
select household_id, campaign_id, campaign_type, start_date, end_date,
       cast(floor(date_diff('day', date '2017-01-01', start_date) / 7) + 1 as integer) as start_week,
       cast(floor(date_diff('day', date '2017-01-01', end_date)   / 7) + 1 as integer) as end_week
from {{ ref('stg_campaigns') }}
