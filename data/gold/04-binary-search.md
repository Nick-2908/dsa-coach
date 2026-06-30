# Gold Example 04 — Binary Search  (pattern: halving a sorted search space)

## INPUT (problem, in our own words)
You're given an array of integers sorted in ascending order and a target value. Return the index of
the target if it's present, or -1 if it isn't.

## OUTPUT (the derivation)

## Observations
- The array is **sorted** — that's the single most important fact here.
- We only need to find the target's position (or confirm it's absent).
- Sorted order means the elements carry structure we can exploit, not just a flat list to scan.

## Brute force
- Walk the array from left to right, comparing each element to the target until you find it or run
  out. Time O(n), Space O(1). It works — but it completely ignores that the array is sorted.

## Bottleneck
- The linear scan throws away the sorted structure. It checks elements one at a time even though,
  the moment we look at any element, sortedness already tells us whether the target must be to its
  left or its right. We keep examining regions we could have ruled out instantly.

## Key insight
- Look at the middle element. If it equals the target, done. If the target is larger, it can only
  be in the right half; if smaller, only in the left half. Either way, a single comparison lets us
  discard half of the remaining candidates — then repeat on the half that's left.

## Pattern
- Binary search over a sorted (or monotonic) space.
- Recognition cue: sorted input, or any property that's monotonic (a yes/no that flips exactly
  once) + you're searching → halve the candidate range each step instead of scanning.

## Optimized approach
- Keep `lo = 0` and `hi = n - 1`.
- While `lo <= hi`:
  - `mid = lo + (hi - lo) / 2`  (written this way to avoid overflow).
  - If `a[mid] == target`, return `mid`.
  - If `a[mid] < target`, the target is to the right → set `lo = mid + 1`.
  - Otherwise it's to the left → set `hi = mid - 1`.
- If the loop ends, return -1.

## Complexity
- Time: O(log n)   Space: O(1)

## Generalizable lesson
- When the data is sorted (or a condition is monotonic), don't scan — **halve**. Seeing "sorted
  input" in a problem is a loud hint to think binary search, and the same halving idea extends to
  searching for boundaries and answers, not just exact values.
