# 🔒 Auditoría de Seguridad — Backend (one-piece-tcg-server)

**Fecha:** 2026-06-06
**Rama:** `feature/security-audit`
**Alcance:** JWT, hashing, rate limiting, validaciones, control de acceso, ownership, sanitización, variables sensibles, logs, endpoints.

---

## Resumen ejecutivo

La postura de seguridad del backend es **sólida**. Se detectó **1 hallazgo crítico** (credencial de base de datos de producción expuesta en el repositorio público) que requiere acción inmediata, además de varias verificaciones de despliegue.

| Severidad | Cantidad |
|---|---|
| 🔴 Crítico | 1 |
| 🟠 Alto | 2 |
| 🟡 Medio | 2 |
| 🔵 Bajo | 2 |
| ✅ Correcto (sin acción) | 10 |

---

## 🔴 CRÍTICO

### C-1. Credencial de BD de producción hardcodeada en el repositorio

- **Dónde:** `scripts/import_cards.py` (trackeado en git, **historial público**), `scripts/import_cards_optimized.py`, `scripts/import_op13_to_op16.py`.
- **Qué:** `os.getenv("DB_PASS", "<contraseña real de Railway>")` — la contraseña de PostgreSQL de producción estaba como valor por defecto en texto plano.
- **Impacto:** El repo `one-piece-tcg-server` es **público**. Cualquiera podía leer la contraseña y acceder a la base de datos de producción (lectura/escritura/borrado de todos los usuarios y datos).
- **Fix aplicado (este commit):** Se eliminó la credencial por defecto de los 3 scripts; ahora exigen `DB_PASS` por variable de entorno y abortan si falta.
- **⚠️ ACCIÓN OBLIGATORIA DEL USUARIO (no automatizable):**
  1. **Rotar YA la contraseña** de PostgreSQL en Railway. La actual está comprometida (sigue en el **historial de git** aunque se haya quitado del archivo).
  2. Actualizar la variable `DATABASE_URL` / `DB_PASS` en el entorno de Railway con la nueva contraseña.
  3. (Opcional, avanzado) Reescribir el historial de git para purgar la credencial (`git filter-repo`), o considerar el repo comprometido y rotar todo secreto que haya tocado.

---

## 🟠 ALTO

### A-1. Verificar `SECRET_KEY` en producción
- **Estado:** El código YA valida y **aborta el arranque** si `SECRET_KEY` es el valor por defecto y `ENVIRONMENT=production` (`config.py: validate_security`). ✅ Buen diseño.
- **Acción:** Confirmar que en Railway están seteadas `SECRET_KEY` (valor único y secreto) y `ENVIRONMENT=production`.

### A-2. Verificar CORS en producción
- **Estado:** `CORS_ORIGINS` es configurable por env; por defecto apunta a localhost.
- **Riesgo:** Si en producción quedara `*` o incluyera orígenes no confiables, habría exposición.
- **Acción:** Confirmar que `CORS_ORIGINS` en Railway lista solo los orígenes legítimos (no `*`).

---

## 🟡 MEDIO

### M-1. Lockout de login en memoria
- **Dónde:** `core/rate_limiter.py` (`_failed_attempts: dict`).
- **Detalle:** El bloqueo por intentos fallidos vive en memoria del proceso → se reinicia al redeploy y **no se comparte entre múltiples instancias**.
- **Impacto:** Aceptable para despliegue de **una sola instancia**. Si se escala horizontalmente, el lockout pierde efectividad.
- **Recomendación:** Si se escala, mover el estado de rate-limit/lockout a Redis.

### M-2. Rate limiting (slowapi) en memoria
- **Detalle:** `Limiter(key_func=get_remote_address)` usa almacenamiento en memoria por defecto.
- **Impacto:** Igual que M-1: por instancia. OK para single-instance.
- **Recomendación:** Backend de Redis si se escala.

---

## 🔵 BAJO

### B-1. Enumeración de usuarios (verificar)
- **Acción:** Confirmar que los mensajes de error de login/registro/reset no revelen si un email/usuario existe (mensajes genéricos). No se verificó en detalle en esta pasada.

### B-2. Defaults de host/usuario en scripts
- **Detalle:** Tras el fix, los scripts aún traen `DB_HOST`/`DB_NAME`/`DB_USER` por defecto (no secretos, pero exponen infraestructura).
- **Recomendación:** Moverlos también a env si se desea ocultar el host.

---

## ✅ CORRECTO (verificado, sin acción)

| # | Control | Estado |
|---|---|---|
| 1 | Hashing de contraseñas | ✅ bcrypt (`gensalt` + `checkpw`) |
| 2 | JWT | ✅ HS256, access 15 min + refresh 30 d |
| 3 | Validación de `SECRET_KEY` | ✅ aborta en prod si es default |
| 4 | Rate limiting | ✅ login 5/min, registro 3/min (slowapi) |
| 5 | Lockout de login | ✅ 10 intentos → 15 min de bloqueo |
| 6 | Endpoints admin | ✅ protegidos con `require_admin` (chequea `is_admin`) |
| 7 | Ownership de carpetas | ✅ `_get_own_folder(folder_id, user_id)` en patch/delete/get/put — sin IDOR |
| 8 | Inyección SQL | ✅ SQLAlchemy parametrizado; sin f-strings/format en queries |
| 9 | Secretos en repo | ✅ `.gitignore` excluye `.env` / `.env.*` |
| 10 | Logs | ✅ sin password/token/secret en logs; `DATABASE_URL` por env (placeholder localhost seguro) |
| 11 | HTTPS | ✅ provisto por Railway |

---

## Checklist de acciones (post-auditoría)

- [x] Quitar credencial hardcodeada de los 3 scripts (aplicado en este commit).
- [x] Agregar `*.log` a `.gitignore` (evita subir logs de import).
- [ ] **ROTAR la contraseña de PostgreSQL en Railway** (CRÍTICO — usuario).
- [ ] Verificar `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS` en Railway.
- [ ] (Opcional) Purgar la credencial del historial git (`git filter-repo`).
- [ ] (Si se escala) Mover rate-limit/lockout a Redis.
