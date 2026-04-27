# Guía paso a paso — Servidor One Piece TCG

## Lo que necesitas instalar antes

- **Python 3.12** → https://python.org/downloads
- **Docker Desktop** → https://docker.com/products/docker-desktop
  _(Docker se usa para la base de datos PostgreSQL, es lo más simple)_

---

## PASO 1 — Copiar los archivos del servidor

Crea una carpeta en tu computador, por ejemplo `C:\op-tcg-server\`, y copia ahí todos los archivos de este zip.

La estructura debe quedar así:
```
op-tcg-server/
  app/
    __init__.py
    main.py
    database.py
    models.py
    routers/
      __init__.py
      cards.py
      decks.py
  scripts/
    import_cards.py
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env.example
```

---

## PASO 2 — Levantar la base de datos con Docker

Abre una terminal dentro de la carpeta `op-tcg-server` y ejecuta:

```bash
docker compose up -d db
```

Esto descarga PostgreSQL y lo inicia en segundo plano.
Solo se hace una vez (o cada vez que reinicias Docker).

Verifica que esté corriendo:
```bash
docker compose ps
```
Debe aparecer `db` con estado `running`.

---

## PASO 3 — Instalar dependencias de Python

En la misma terminal:

```bash
pip install -r requirements.txt
```

---

## PASO 4 — Importar las cartas (solo se hace una vez)

Este script descarga todas las cartas desde la API pública y las guarda en tu base de datos:

```bash
python scripts/import_cards.py
```

Verás algo así:
```
Importando OP01... ✓ 121 cartas
Importando OP02... ✓ 121 cartas
...
Importación completa: 2847 cartas
```

**Cuando salgan sets nuevos**, agrega el código al archivo `scripts/import_cards.py` en la lista `KNOWN_SETS` y vuelve a ejecutar el script. Las cartas existentes se actualizan, no se duplican.

---

## PASO 5 — Iniciar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verás:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

El servidor está funcionando. Deja esta terminal abierta mientras lo uses.

---

## PASO 6 — Probar que funciona

Abre tu navegador y entra a:

```
http://localhost:8000
```
→ Debe responder: `{"status": "ok", "message": "One Piece TCG API funcionando"}`

```
http://localhost:8000/cards/OP14-079
```
→ Debe responder con los datos completos de esa carta.

```
http://localhost:8000/docs
```
→ **Documentación interactiva automática** donde puedes probar todos los endpoints.

---

## Endpoints disponibles

| Método | URL | Para qué sirve |
|--------|-----|----------------|
| GET | `/cards/OP14-079` | Buscar carta por código (lo que usará el scanner) |
| GET | `/cards/?q=Luffy` | Buscar cartas por nombre |
| GET | `/cards/set/OP14` | Todas las cartas de un set |
| POST | `/decks/resolve` | Resolver una lista de códigos tipo mazo |
| POST | `/decks/` | Guardar un mazo |
| GET | `/decks/` | Ver todos los mazos guardados |
| GET | `/decks/1` | Ver un mazo con cartas resueltas |
| DELETE | `/decks/1` | Eliminar un mazo |

---

## Para usarlo desde la app Flutter

La URL base que debes poner en la app es:

- **Pruebas locales (emulador Android):** `http://10.0.2.2:8000`
- **Pruebas en celular físico:** `http://LA-IP-DE-TU-PC:8000`
  _(para ver tu IP: ejecuta `ipconfig` en Windows, busca "IPv4")_
- **Producción (servidor en internet):** la URL de tu VPS o servicio cloud

---

## Subir el servidor a internet (cuando estés listo)

La opción más simple y económica es **Railway** (gratis para empezar):

1. Crea cuenta en https://railway.app
2. Conecta tu repositorio de GitHub con estos archivos
3. Agrega una base de datos PostgreSQL desde Railway
4. Railway te da una URL pública automáticamente

Otras opciones: Render.com, Fly.io, o un VPS de DigitalOcean/Linode.

---

## Solución de problemas comunes

**"Connection refused" al iniciar el servidor:**
→ Asegúrate de que Docker esté corriendo y hayas ejecutado `docker compose up -d db`

**"Carta no encontrada" para un código que debería existir:**
→ Vuelve a ejecutar `python scripts/import_cards.py` para actualizar los datos

**El emulador Android no puede conectar al servidor:**
→ Usa `http://10.0.2.2:8000` en lugar de `http://localhost:8000`
→ En celular físico usa la IP de tu PC (ver sección arriba)
