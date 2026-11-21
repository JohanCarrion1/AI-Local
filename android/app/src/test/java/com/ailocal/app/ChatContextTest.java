package com.ailocal.app;

import static org.junit.Assert.*;

import org.json.*;
import org.junit.Test;

public class ChatContextTest {
  private JSONObject request(String question) throws Exception {
    return new JSONObject()
        .put(
            "messages",
            new JSONArray()
                .put(
                    new JSONObject()
                        .put("role", "system")
                        .put("content", "Prefiero respuestas breves."))
                .put(new JSONObject().put("role", "user").put("content", question)));
  }

  @Test
  public void missingCredentialsDescribesTheActualAppWorkflow() throws Exception {
    JSONObject result = ChatContext.prepare(request("¿Puedes conectarte a GitHub?"), false, "");
    String system = result.getJSONArray("messages").getJSONObject(0).getString("content");
    assertTrue(system.contains("no hay token"));
    assertTrue(system.contains("Menú > Conectar a GitHub"));
    assertTrue(system.contains("Prefiero respuestas breves."));
    assertTrue(system.contains("La app SÍ integra GitHub"));
  }

  @Test
  public void selectedFileAndNativeAccountStateReachTheModelWithoutCredentials() throws Exception {
    String secret = "github_pat_" + "x".repeat(50), classic = "ghp_" + "a".repeat(36);
    JSONObject input = request("Mi código contiene " + secret);
    input.put(
        "workspace",
        new JSONObject()
            .put("repo", "owner/repo")
            .put("branch", "dev")
            .put("path", "src/main.js")
            .put("sha", "abc")
            .put("text", "const token = '" + classic + "';"));
    JSONObject result = ChatContext.prepare(input, true, "johan");
    assertFalse(result.toString().contains(secret));
    assertFalse(result.toString().contains(classic));
    JSONArray messages = result.getJSONArray("messages");
    assertTrue(
        messages.getJSONObject(0).getString("content").contains("cuenta configurada (johan)"));
    assertTrue(messages.getJSONObject(1).getString("content").contains("src/main.js"));
    assertTrue(messages.getJSONObject(1).getString("content").contains("no lectura en vivo"));
    assertTrue(
        result.getJSONObject("workspace").getString("text").contains("[token de GitHub oculto]"));
    assertTrue(
        input.toString().contains(secret)); // preparing the request does not mutate stored history
  }

  @Test
  public void ordinaryCodeAndPlaceholdersRemainUsable() {
    assertEquals(
        "github_pat_… const github_token = value;",
        ChatContext.redact("github_pat_… const github_token = value;"));
  }
}
