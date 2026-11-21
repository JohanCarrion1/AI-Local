package com.ailocal.app;

/** Live headroom with an explicit margin; estimates never act as a compatibility ban. */
final class ResourceBudget {
  static final long GIB = 1024L * 1024 * 1024;
  static final long MIB = 1024L * 1024;

  static long reserve(long total, long lowMemoryThreshold) {
    return Math.max(256 * MIB, (long) (Math.max(0, lowMemoryThreshold) * 1.10));
  }

  static long usable(
      long total,
      long available,
      long threshold,
      long cgroupHeadroom,
      boolean lowMemory,
      boolean pressure) {
    if (total <= 0 || available <= 0) return 0;
    long budget = Math.max(0, Math.min(available, total) - reserve(total, threshold));
    if (cgroupHeadroom >= 0) budget = Math.min(budget, Math.max(0, cgroupHeadroom - 128 * MIB));
    // PSI and lowMemory are reported separately; do not invent a percentage ceiling.
    return budget;
  }
}
