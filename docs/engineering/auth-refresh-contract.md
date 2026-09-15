# Frontend Auth Refresh Contract

The web client only attempts `/auth/refresh` after a `401` response when a refresh token is actually present.

Local backend login intentionally returns `refreshToken: null`. In that mode, an expired or rejected access token must surface the original `401` instead of triggering a refresh request that the local backend does not implement.

When several requests fail with `401` while a refresh token exists, concurrent requests wait for the single refresh operation. A refresh failure rejects all queued requests and clears the local authentication state.
