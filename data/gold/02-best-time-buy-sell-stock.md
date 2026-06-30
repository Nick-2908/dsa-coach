# Gold Example 02 — Best Time to Buy and Sell Stock  (pattern: one-pass running minimum)

## INPUT (problem, in our own words)
You're given an array where the i-th entry is a stock's price on day i. You may buy on one day and
sell on a *later* day (at most one buy and one sell). Return the maximum profit you can make. If no
profitable trade exists, return 0.

## OUTPUT (the derivation)

## Observations
- You must buy before you sell, so the sell day's index has to be greater than the buy day's.
- We want the largest value of (price on a later day) - (price on an earlier day).
- Only one transaction is allowed, so we're looking for a single best buy/sell pair.

## Brute force
- Try every pair of days (i, j) with j > i, compute the profit prices[j] - prices[i], and keep the
  maximum. Two nested loops. Time O(n^2), Space O(1).

## Bottleneck
- For each potential sell day, we re-scan all earlier days to find the cheapest buy price. That
  repeated search for "the minimum price before today" is the wasted work — we recompute the same
  running minimum over and over.

## Key insight
- Sweep left to right once. For any day, the best possible buy price is simply the lowest price
  seen so far. We can carry that minimum along as we go, so at each day the best profit if we sell
  today is just (today's price - cheapest price seen so far) — no re-scanning needed.

## Pattern
- One-pass scan carrying a running aggregate (here, a running minimum).
- Recognition cue: when the brute force keeps re-searching the elements *before* the current one
  for a min / max / sum, carry that aggregate forward in a single pass instead.

## Optimized approach
- Track `minPrice = +infinity` and `best = 0`.
- Walk the prices once. For each price:
  - Update `best = max(best, price - minPrice)` (profit if we sold today).
  - Update `minPrice = min(minPrice, price)` (cheapest buy seen so far).
- Return `best`.

## Complexity
- Time: O(n)   Space: O(1)

## Generalizable lesson
- When you need the best "partner" from everything seen *before* the current element, maintain a
  running min/max/sum in a single pass instead of re-scanning the prefix each time. This collapses
  an O(n^2) pair search into O(n).
