select c.household_id, c.campaign_id, d.campaign_type, d.start_date, d.end_date
from {{ source('raw', 'campaigns') }} c
join {{ source('raw', 'campaign_descriptions') }} d using (campaign_id)
