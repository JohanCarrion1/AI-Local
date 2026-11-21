package com.ailocal.app;

import static org.junit.Assert.*;

import org.junit.Test;

public class ResourceBudgetTest {
  private long gb(double value) {
    return (long) (value * ResourceBudget.GIB);
  }

  @Test
  public void screenshotUsesFreeMemoryNotPhysicalRam() {
    long budget = ResourceBudget.usable(gb(7.2), gb(2.5), gb(.2), -1, false, false);
    assertTrue(budget > 0);
    assertTrue(budget < gb(2.5));
    assertEquals(gb(2.5) - ResourceBudget.reserve(gb(7.2), gb(.2)), budget);
  }

  @Test
  public void eightGbClassPhoneNeverAssumesAllRamUsable() {
    long budget = ResourceBudget.usable(gb(7.2), gb(7.0), gb(.2), -1, false, false);
    assertTrue(budget <= gb(4.5));
    assertTrue(ResourceBudget.usable(gb(7.2), gb(4.5), gb(.2), -1, false, false) < gb(4.5));
  }

  @Test
  public void lowMemoryAndCgroupLimitsReduceBudget() {
    assertEquals(0, ResourceBudget.usable(gb(7.2), gb(4.5), gb(.2), -1, true, false));
    long limited = ResourceBudget.usable(gb(7.2), gb(4.5), gb(.2), gb(1), false, false);
    assertEquals(gb(1) - 128 * ResourceBudget.MIB, limited);
    long normal = ResourceBudget.usable(gb(7.2), gb(4.5), gb(.2), -1, false, false);
    assertTrue(ResourceBudget.usable(gb(7.2), gb(4.5), gb(.2), -1, false, true) < normal);
  }

  @Test
  public void missingMemoryNeverBecomesRecommendedBudget() {
    assertEquals(0, ResourceBudget.usable(0, 0, 0, -1, false, false));
    assertEquals(0, ResourceBudget.usable(gb(7.2), -1, 0, -1, false, false));
    assertEquals(0, ResourceBudget.usable(gb(7.2), gb(.1), gb(.2), -1, false, false));
  }
}
