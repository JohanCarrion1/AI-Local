package com.ailocal.app;

import android.app.ActivityManager;
import android.content.Context;
import android.os.Build;
import android.os.Debug;
import java.io.*;
import org.json.JSONObject;

/** Live OS measurements with optional procfs/cgroup signals and explicit fallbacks. */
final class ResourceMonitor {
  private static String read(String path) {
    try (BufferedReader in = new BufferedReader(new FileReader(path))) {
      StringBuilder text = new StringBuilder();
      String line;
      while ((line = in.readLine()) != null && text.length() < 65536)
        text.append(line).append('\n');
      return text.toString();
    } catch (IOException | SecurityException unavailable) {
      return "";
    }
  }

  private static long memAvailable() {
    for (String line : read("/proc/meminfo").split("\n")) {
      if (line.startsWith("MemAvailable:")) {
        try {
          return Long.parseLong(line.trim().split("\\s+")[1]) * 1024;
        } catch (RuntimeException ignored) {
          return -1;
        }
      }
    }
    return -1;
  }

  private static long cgroupHeadroom() {
    // Android commonly denies these files or does not impose a per-app cgroup limit.
    // Missing/"max" is unknown, not zero and not an invented per-process allowance.
    long smallest = -1;
    for (String line : read("/proc/self/cgroup").split("\n")) {
      if (!line.startsWith("0::")) continue;
      String relative = line.substring(3);
      if (!relative.startsWith("/") || relative.contains("..")) continue;
      File dir = new File("/sys/fs/cgroup" + relative);
      for (int depth = 0; depth < 12 && dir != null; depth++, dir = dir.getParentFile()) {
        String limit = read(new File(dir, "memory.max").getPath()).trim();
        String used = read(new File(dir, "memory.current").getPath()).trim();
        try {
          if (!limit.isEmpty() && !limit.equals("max") && !used.isEmpty()) {
            long room = Math.max(0, Long.parseLong(limit) - Long.parseLong(used));
            smallest = smallest < 0 ? room : Math.min(smallest, room);
          }
        } catch (NumberFormatException ignored) {
        }
        if (dir.getPath().equals("/sys/fs/cgroup")) break;
      }
    }
    return smallest;
  }

  private static double pressure(String data, String kind) {
    for (String line : data.split("\n"))
      if (line.startsWith(kind + " ")) {
        for (String field : line.split(" "))
          if (field.startsWith("avg10=")) {
            try {
              return Double.parseDouble(field.substring(6));
            } catch (NumberFormatException ignored) {
              return -1;
            }
          }
      }
    return -1;
  }

  static JSONObject sample(Context context) throws Exception {
    ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
    ((ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE)).getMemoryInfo(memory);
    long procAvailable = memAvailable();
    long available =
        procAvailable >= 0 ? Math.min(memory.availMem, procAvailable) : memory.availMem;
    long headroom = cgroupHeadroom();
    String psi = read("/proc/pressure/memory");
    double some = pressure(psi, "some"), full = pressure(psi, "full");
    boolean pressured = some >= 10 || full >= 1;
    long budget =
        ResourceBudget.usable(
            memory.totalMem, available, memory.threshold, headroom, memory.lowMemory, pressured);
    return new JSONObject()
        .put("ram", memory.totalMem / (double) ResourceBudget.GIB)
        .put("available", available / (double) ResourceBudget.GIB)
        .put("budget", budget / (double) ResourceBudget.GIB)
        .put(
            "reserve",
            ResourceBudget.reserve(memory.totalMem, memory.threshold) / (double) ResourceBudget.GIB)
        .put("lowMemory", memory.lowMemory)
        .put("pressure", pressured)
        .put("pressureKnown", some >= 0 || full >= 0)
        .put("psiSome", some)
        .put("psiFull", full)
        .put("cgroupHeadroom", headroom < 0 ? -1 : headroom / (double) ResourceBudget.GIB)
        .put("pssMiB", Debug.getPss() / 1024.0)
        .put("nativeMiB", Debug.getNativeHeapAllocatedSize() / (double) ResourceBudget.MIB)
        .put(
            "source",
            procAvailable >= 0
                ? "ActivityManager + /proc/meminfo"
                : "ActivityManager (procfs no disponible)")
        .put("device", Build.MANUFACTURER + " " + Build.MODEL);
  }
}
