package com.ailocal.app;

/** Conservative estimate for native inference; total RAM is never an allocation limit. */
final class ResourceBudget {
  static final long GIB = 1024L * 1024 * 1024;
  static final long MIB = 1024L * 1024;

  static long reserve(long total, long lowMemoryThreshold) {
    return Math.max(512 * MIB, Math.max((long) (total * 0.08), (long) (lowMemoryThreshold * 1.25)));
  }

  static long usable(
      long total,
      long available,
      long threshold,
      long cgroupHeadroom,
      boolean lowMemory,
      boolean pressure) {
    if (total <= 0 || available <= 0 || lowMemory) return 0;
    // Leave space for Android and other applications even when MemAvailable is high.
    // On an 8 GB-class phone this caps the estimate below 4.5 GiB; it is not an OS limit.
    long ceiling = Math.max(0, Math.min((long) (total * 0.60), total - 1536 * MIB));
    long budget =
        Math.min(ceiling, Math.max(0, Math.min(available, total) - reserve(total, threshold)));
    if (cgroupHeadroom >= 0) budget = Math.min(budget, Math.max(0, cgroupHeadroom - 128 * MIB));
    if (pressure) budget = (long) (budget * 0.75);
    return Math.max(0, budget);
  }
}
