# Auth

The app uses password authorization by default. The password is stored in a file in encrypted form.

On the first start, when password auth is enabled and the password file does not exist yet, the app writes a one-time setup code to the log at warning level. The code is valid for 5 minutes. Enter it on the initial setup screen together with the new password. If the code expires, restart the container to generate a new one. The app does not create another code until the process starts again. Changing the password later, while signed in, does not require this code.

Alternatively, you can use an OpenID Connect provider instead of a password.

Auth cookies are not domain-specific and not HTTPS-only. All of this can be configured using env variables.
