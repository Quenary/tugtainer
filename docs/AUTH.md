# Auth

Password authorization is the default. The password is stored encrypted in a file (`PASSWORD_FILE`).

On the first start, when password auth is enabled and that file does not exist, the app writes a one-time setup code to the log at warning level. The code is valid for 5 minutes. The setup screen accepts it together with the new password. An expired code is replaced only when the process starts again. A later password change, while signed in, does not use the code.

`OIDC_ENABLED` replaces the password with an OpenID Connect provider.

Auth cookies are not bound to a domain and are not HTTPS-only until `DOMAIN` and `HTTPS` say otherwise. `DISABLE_AUTH` turns the check off.
