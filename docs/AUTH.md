# Auth

The app uses password authorization by default. The password is stored in a file in encrypted form.

Alternatively, you can use an OpenID Connect provider instead of a password.

Auth cookies are not domain-specific and not HTTPS-only. All of this can be configured using env variables.
