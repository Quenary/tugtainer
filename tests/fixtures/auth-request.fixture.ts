import { test as base, type APIRequestContext } from '@playwright/test';

/** Meets backend password_validator (upper + lower + digit). */
export const TEST_PASSWORD = 'TestPass1';

/**
 * Ensure the API request context has an authenticated session cookie.
 * Sets the UI password on a fresh volume, then logs in.
 */
export async function login(request: APIRequestContext): Promise<void> {
  const passwordSet = await request.get('/api/auth/is_password_set');
  if (!passwordSet.ok()) {
    throw new Error(
      `is_password_set failed: ${passwordSet.status()} ${await passwordSet.text()}`,
    );
  }

  if (!(await passwordSet.json())) {
    const setRes = await request.post('/api/auth/set_password', {
      data: {
        password: TEST_PASSWORD,
        confirm_password: TEST_PASSWORD,
      },
    });
    if (!setRes.ok()) {
      throw new Error(
        `set_password failed: ${setRes.status()} ${await setRes.text()}`,
      );
    }
  }

  const loginRes = await request.post('/api/auth/password/login', {
    data: { password: TEST_PASSWORD },
  });
  if (!loginRes.ok()) {
    throw new Error(
      `login failed: ${loginRes.status()} ${await loginRes.text()}`,
    );
  }
}

/** Drop the session cookies of the request context. */
export async function logout(request: APIRequestContext): Promise<void> {
  const res = await request.post('/api/auth/logout');
  if (!res.ok()) {
    throw new Error(`logout failed: ${res.status()} ${await res.text()}`);
  }
}

/**
 * Logged in request context. Logs out on teardown, so auth tests can rely on
 * a clean session state regardless of what the test did.
 */
export const test = base.extend<{ authorizedRequest: APIRequestContext }>({
  authorizedRequest: async ({ request }, use) => {
    await login(request);
    try {
      await use(request);
    } finally {
      await logout(request);
    }
  },
});
