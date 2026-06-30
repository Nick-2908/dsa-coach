# Gold Example 03 — Longest Substring Without Repeating Characters  (pattern: sliding window)

## INPUT (problem, in our own words)
Given a string, find the length of the longest *contiguous* substring that contains no repeated
characters. For example, in "abcabcbb" the answer is 3 ("abc"). Note: substring means a
continuous run of characters, not a subsequence.

## OUTPUT (the derivation)

## Observations
- We want the *length* of the longest run, not the substring itself.
- "Substring" is contiguous, so the answer is some window [left, right] of the string.
- The constraint is local: a window is valid as long as no character repeats inside it.

## Brute force
- Consider every possible substring (every start, every end), and for each, check whether all its
  characters are unique using a set. Keep the longest valid one.
- There are O(n^2) substrings and each uniqueness check costs up to O(n). Time O(n^2) (O(n^3) if
  you re-scan naively), Space O(n) for the set.

## Bottleneck
- Huge overlap of work. When we extend a substring and hit a repeat, we throw the whole thing away
  and restart from the next index — re-scanning characters we had *already* verified as unique a
  moment ago. We keep re-validating the same overlapping ranges.

## Key insight
- Keep a single window that is *always* duplicate-free, and never restart from scratch. When a new
  character on the right would create a duplicate, don't reset — just shrink the window from the
  left until the duplicate is gone. The already-validated middle of the window is reused, not
  rebuilt. Both ends only ever move forward, so each character enters and leaves the window at
  most once.

## Pattern
- Sliding window (variable size) + a set/map of the characters currently inside it.
- Recognition cue: "longest/shortest **contiguous** substring or subarray satisfying a property"
  where the property can be maintained incrementally as you grow or shrink the span → reach for a
  sliding window with two forward-only pointers.

## Optimized approach
- Keep `left = 0`, a set of characters currently in the window, and `best = 0`.
- Move `right` across the string one character at a time:
  - While `s[right]` is already in the set, remove `s[left]` from the set and advance `left`
    (shrink the window until the duplicate is gone).
  - Add `s[right]` to the set.
  - Update `best = max(best, right - left + 1)` (the current window size).
- (Optimization: a "last seen index" map lets `left` jump directly past the duplicate instead of
  stepping one at a time.)

## Complexity
- Time: O(n)   Space: O(min(n, alphabet size))

## Generalizable lesson
- When a brute force keeps *restarting and re-scanning overlapping ranges*, a sliding window
  reuses the validated portion by only ever advancing two pointers — collapsing O(n^2) into O(n).
  This is the go-to move for "longest/shortest contiguous span with a property" problems.
