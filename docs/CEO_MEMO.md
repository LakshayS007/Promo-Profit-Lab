# Memo: promotions pay back only when suppliers fund a third of them

**To:** CEO, CFO, Category Director  **From:** Lakshay Saini, Analytics  **Re:** Promotion ROI, 2017 (2,469-household shopper panel)

*Portfolio case study on public data (84.51° The Complete Journey). The memo is written as if for the retailer's leadership; the numbers are real, and the stakeholders are illustrative.*

## The answer

**Promotions break even only if suppliers fund about a third (33%) of the extra discount.** We fund all of it in this data, so every $1 of promotion spend returns **−33¢** of gross profit (90% range −35¢ to −31¢). That is **−$327k for every $1M** we spend.

The new sales are not the problem. The margin on the extra units almost covers the discount on them. The loss is the discount handed to shoppers who would have bought anyway: **45% of promoted units**.

| Where each $1 of promotion spend goes | |
|---|---|
| Margin earned on the extra units | +69¢ |
| Extra discount on those extra units | −64¢ |
| Extra discount to shoppers who would have bought anyway | −36¢ |
| Margin taken from rival items in the same category | −4¢ |
| Repeat buying in the 2 weeks after | +2¢ |
| **Net** | **−33¢** |

Three findings shape what to do:

- **Displays and deli promotions pay their way; price cuts do not.** In-store displays return +15¢ per $1. Price cuts with no mailer or display return −47¢, because 56% of their units would have sold anyway.
- **"Promotions bring shoppers in" does not hold here.** When more of a household's usual basket is on promotion, it buys more of the promoted items, but its spend on everything else does not rise. Even the top of the range (+4¢ per $1) leaves promotions at −29¢.
- **Half of what looked like promotion cost is everyday pricing.** 51% of card discounts on core products are a product's normal card price. Promotion spend here counts only the discount beyond that.

**Targeted campaigns are not proven.** Campaign households already spent 3.5× more than others before being targeted. Measured properly, Type A campaigns add +$0.34 a week per household (95% range −$1.14 to +$1.82), below the smallest effect this data can detect ($2.12).

## What I recommend

| # | Action | Value per $1M of promotion spend | Risk and how to manage it |
|---|---|---|---|
| 1 | **Make supplier funding the entry ticket.** A promotion runs only if its supplier covers its break-even share: 0% for displays and deli, up to 59% for grocery price cuts. | Every line pays back at its target. At 50% funding across the board, the panel goes from −$54k to +$29k | Suppliers may refuse. Start with the 6 Keep lines, which need 25% or less. |
| 2 | **Cut the extra discount by 5 points on the 8 Fix lines and move budget to lines that lose least.** At 25% supplier funding or less, the profit-maximising extra discount is zero in every department. | +$108k from shallower discounts + $46k from reallocation = **+$153k, 47% of the loss**, with no new money | Less volume and a weaker price image. Traffic categories keep at least 80% of today's spend; track weekly basket count. |
| 3 | **Hold out a random 10–20% of households from every campaign.** | Turns campaign spend into a measured return in one 6-week cycle. A Type A contact that costs more than $4.26 cannot pay back even at the top of today's range | Needs about 7,850 households per group to detect a 3% lift, using each household's prior spend as a baseline (CUPED). |

## What this does not cover

- **Costs and funding are assumptions.** Margins are industry benchmarks (grocery 25%, produce 40%, meat 28%, deli 40%, bakery 55%), because the data has no cost prices. Even at +10 points of margin, promotions lose 9¢ per $1 without supplier funding.
- **Not observed:** supplier funding actually received, mailing costs, competitor prices, and effects beyond two weeks.
- **Scope:** one retailer, one year (2017), a household panel rather than full store sales. The pilot in recommendation 2 measures the result directly before scaling.

Full analysis, code and dashboard: see the repository README.
