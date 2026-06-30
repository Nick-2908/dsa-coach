# Gold Example 05 — Climbing Stairs  (pattern: dynamic programming / recurrence)

## INPUT (problem, in our own words)
You're climbing a staircase with n steps. Each move you can climb either 1 step or 2 steps. How
many distinct ways are there to reach the top? (Order matters: 1-then-2 is different from
2-then-1.)

## OUTPUT (the derivation)

## Observations
- We're counting the number of distinct ordered sequences of 1s and 2s that sum to n.
- The answer for n feels like it should relate to the answers for smaller staircases.
- Order matters, so we count sequences, not combinations.

## Brute force
- Recurse: to count the ways to reach step n, your final move was either a 1-step (from n-1) or a
  2-step (from n-2), so ways(n) = ways(n-1) + ways(n-2), with ways(0) = 1 and ways(1) = 1.
- Computed naively as plain recursion, this recomputes the same subproblems again and again.
  Time O(2^n), Space O(n) for the call stack.

## Bottleneck
- The naive recursion tree is full of overlap: ways(n-2) is recomputed by both ways(n) and
  ways(n-1), and that duplication explodes exponentially. We solve identical subproblems many
  times.

## Key insight
- The answer to each subproblem never changes, so compute it **once** and reuse it. Either store
  results as you recurse (memoization) or build them up from the bottom (ways(2), ways(3), …,
  ways(n)). This is exactly the Fibonacci recurrence in disguise.

## Pattern
- Dynamic programming: a recurrence over overlapping subproblems.
- Recognition cue: the answer for n is built from the answers to smaller inputs, AND those smaller
  subproblems repeat → memoize (top-down) or tabulate (bottom-up) so each is solved once.

## Optimized approach
- Handle tiny cases: if n <= 1, the answer is 1.
- Keep two rolling values: `a = ways(0) = 1`, `b = ways(1) = 1`.
- For i from 2 to n: `c = a + b; a = b; b = c`.
- Return `b`. (We only ever need the previous two answers, so no full array is required.)

## Complexity
- Time: O(n)   Space: O(1)  (rolling two variables instead of a full table)

## Generalizable lesson
- When a problem's answer is assembled from smaller, overlapping subproblems, write down the
  recurrence and reuse subresults (DP) instead of recomputing them — turning exponential work into
  linear. If you only depend on the last few subproblems, you can drop the table down to a couple
  of variables.
