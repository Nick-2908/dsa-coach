# Gold Example 01 — Two Sum  (pattern: hash map / complement lookup)

## INPUT (problem, in our own words)
You're given an array of integers and a target value. Return the indices of the two numbers
that add up to the target. Assume exactly one valid pair exists, and you can't use the same
element twice.

## OUTPUT (the derivation)

## Observations
- We need a *pair* of elements whose sum equals the target, and we must return their indices.
- Exactly one solution exists, so we don't have to handle "no answer" or multiple answers.
- Nothing says the array is sorted — so we can't assume order.

## Brute force
- Try every pair: for each element, scan the rest of the array for a partner that completes
  the target. Two nested loops. Time O(n^2), Space O(1).

## Bottleneck
- For each element x, we re-scan the array looking for `target - x`. That repeated linear
  search is the wasted work — we keep re-asking "have I seen the number I need?"

## Key insight
- Instead of *searching* for the needed partner each time, *remember* the numbers we've already
  passed. If we store each value as we go, checking "is the partner already seen?" becomes an
  instant lookup instead of a scan.

## Pattern
- Hash map for complement lookup (a "seen" map of value -> index).
- Recognition cue: when brute force keeps **searching for a specific needed value**, a hash map
  trades space for time by remembering what you've seen — turning an O(n) search into O(1).

## Optimized approach
- Create an empty map of value -> index.
- Walk the array once. For the current value x, compute need = target - x.
- If `need` is already in the map, you've found the pair: return [map[need], current index].
- Otherwise, store x -> current index and continue.

## Complexity
- Time: O(n)   Space: O(n)

## Generalizable lesson
- When a brute force repeatedly *re-searches* for a value it needs, ask: "can I remember what
  I've already seen so the lookup is O(1)?" A hash map is the usual answer. This same move powers
  many pair/subarray-sum problems.
