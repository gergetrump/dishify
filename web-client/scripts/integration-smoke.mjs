import http from "node:http";
import https from "node:https";

const apiUrl = process.env.VITE_API_URL || process.env.API_URL || "http://localhost:8000";
const runId = Date.now();
const username = `web_smoke_${runId}`;
const email = `${username}@example.com`;
const password = "smoke-secret-1";

async function main() {
  const health = await request("GET", "/health");
  assertEqual(health.status, 200, "GET /health status");
  assertEqual(health.body.status, "ok", "GET /health body");

  const unauthorizedProfile = await request("GET", "/me");
  assertEqual(unauthorizedProfile.status, 401, "GET /me without token status");

  const register = await request("POST", "/auth/register", {
    username,
    email,
    password,
    exclusion_restrictions: ["vegetarian"],
  });
  assertEqual(register.status, 201, "POST /auth/register status");

  const login = await request("POST", "/auth/login", { username, password });
  assertEqual(login.status, 200, "POST /auth/login status");
  assert(login.body.access_token, "POST /auth/login access_token");
  const token = login.body.access_token;

  const profile = await request("GET", "/me", undefined, token);
  assertEqual(profile.status, 200, "GET /me status");
  assertEqual(profile.body.username, username, "GET /me username");

  const savedPreferences = await request(
    "PUT",
    "/me/preferences",
    { exclusion_restrictions: ["vegetarian", "nut_allergy"] },
    token,
  );
  assertEqual(savedPreferences.status, 200, "PUT /me/preferences status");
  assertArrayIncludes(
    savedPreferences.body.exclusion_restrictions,
    "nut_allergy",
    "PUT /me/preferences saved nut_allergy",
  );

  const loadedPreferences = await request("GET", "/me/preferences", undefined, token);
  assertEqual(loadedPreferences.status, 200, "GET /me/preferences status");
  assertArrayIncludes(
    loadedPreferences.body.exclusion_restrictions,
    "vegetarian",
    "GET /me/preferences saved vegetarian",
  );

  const invalidPreferences = await request(
    "PUT",
    "/me/preferences",
    { exclusion_restrictions: ["not_a_real_restriction"] },
    token,
  );
  assertEqual(invalidPreferences.status, 422, "PUT /me/preferences invalid restriction status");

  const recommendation = await request(
    "POST",
    "/recommend",
    {
      query: "quick vegetarian pasta",
      top_k: 3,
      available_ingredients: [
        {
          name: "pasta",
          quantity: null,
          unit: null,
          raw_text: "pasta",
        },
        {
          name: "tomato",
          quantity: null,
          unit: null,
          raw_text: "tomato",
        },
      ],
    },
    token,
  );
  assertEqual(recommendation.status, 200, "POST /recommend status");
  assert(Array.isArray(recommendation.body.results), "POST /recommend results array");
  assert(Array.isArray(recommendation.body.stages), "POST /recommend stages array");
  assert(recommendation.body.stages.some((stage) => stage.name === "retrieve"), "retrieve stage");

  console.log("Integration smoke test passed");
}

function request(method, path, body, token) {
  const url = new URL(path, apiUrl);
  const payload = body === undefined ? undefined : JSON.stringify(body);
  const transport = url.protocol === "https:" ? https : http;

  return new Promise((resolve, reject) => {
    const req = transport.request(
      url,
      {
        method,
        headers: {
          Accept: "application/json",
          ...(payload
            ? {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(payload),
              }
            : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      },
      (res) => {
        let raw = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          raw += chunk;
        });
        res.on("end", () => {
          let parsed = null;
          if (raw) {
            try {
              parsed = JSON.parse(raw);
            } catch {
              parsed = raw;
            }
          }
          resolve({ status: res.statusCode, body: parsed });
        });
      },
    );

    req.on("error", reject);
    if (payload) {
      req.write(payload);
    }
    req.end();
  });
}

function assert(condition, label) {
  if (!condition) {
    throw new Error(`Assertion failed: ${label}`);
  }
}

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`Assertion failed: ${label}. Expected ${expected}, got ${actual}`);
  }
}

function assertArrayIncludes(values, expected, label) {
  assert(Array.isArray(values), `${label} array`);
  if (!values.includes(expected)) {
    throw new Error(`Assertion failed: ${label}. Missing ${expected}`);
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
