# API

The backend API is served under the `/api` base path.

- Swagger UI: `/api/docs`
- Redoc UI: `/api/redoc`

## Public endpoints

- `GET /api/public/health`
- `GET /api/public/version`
- `GET /api/public/summary` (requires `ENABLE_PUBLIC_API=true`)
- `GET /api/public/update_count` (requires `ENABLE_PUBLIC_API=true`)
- `GET /api/public/is_update_available` (requires `ENABLE_PUBLIC_API=true`)
