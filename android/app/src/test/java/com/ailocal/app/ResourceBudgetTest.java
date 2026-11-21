package com.ailocal.app;

import static org.junit.Assert.*;

import org.junit.Test;

public class ResourceBudgetTest {
  private long gb(double value) {
    return (long) (value * ResourceBudget.GIB);
  }

  @Test
  public void fiveGiBAvailableIsNotArtificiallyCappedAtTwoOrSixtyPercent() {
    long budget = ResourceBudget.usable(gb(7.2), gb(5), gb(.2), -1, false, false);
    assertEquals(gb(4.75), budget);
    assertTrue(budget > gb(4.5));
    assertTrue(budget < gb(5));
  }

  @Test
  public void currentAvailabilityStaysSeparateFromTotal() {
    long budget = ResourceBudget.usable(gb(7.2), gb(2.5), gb(.2), -1, false, false);
    assertEquals(gb(2.25), budget);
  }

  @Test
  public void measuredCgroupLimitsStillConstrainHeadroom() {
    assertEquals(
        gb(1) - 128 * ResourceBudget.MIB,
        ResourceBudget.usable(gb(7.2), gb(5), gb(.2), gb(1), false, false));
  }

  @Test
  public void pressureIsAReportedSignalNotAnInventedPercentageCut() {
    assertEquals(
        ResourceBudget.usable(gb(7.2), gb(5), gb(.2), -1, false, false),
        ResourceBudget.usable(gb(7.2), gb(5), gb(.2), -1, true, true));
  }

  @Test
  public void missingMemoryDoesNotInventFreeRam() {
    assertEquals(0, ResourceBudget.usable(0, 0, 0, -1, false, false));
    assertEquals(0, ResourceBudget.usable(gb(7.2), gb(.1), gb(.2), -1, false, false));
  }
}
