# 📚 Scripts de Importación de Cartas

## 📋 Archivos disponibles

### 1. `import_cards_optimized.py` ⭐ RECOMENDADO
**Versión mejorada y robusta del importador original.**

**Mejoras implementadas:**
- ✅ Mejor manejo de rate limits (backoff exponencial)
- ✅ Detección automática de sets disponibles
- ✅ Validación exhaustiva de datos
- ✅ Progreso visual con ETA
- ✅ Batch commits para mejor performance
- ✅ Logging detallado a archivo
- ✅ Reintentos inteligentes
- ✅ Índices automáticos

---

### 2. `import_op13_to_op16.py` 🎯 ESPECÍFICO
**Importa desde OP13 hasta OP16 (con fallback a OP15).**

**Características:**
- Detección automática de disponibilidad
- Si OP16 existe → importa OP13, OP14, OP15, OP16
- Si OP16 NO existe → importa OP13, OP14, OP15
- Logging específico a `import_op13_to_op16.log`

---

## 🚀 Cómo usar

### Opción A: Importar OP13-OP16 (RECOMENDADO PARA TI)

```bash
# Desde la carpeta del server
cd D:\One Piece Scanner\one_piece_card_server

# Ejecutar
python scripts/import_op13_to_op16.py
```

**Salida esperada:**
```
[2024-01-20 10:30:45] [INFO] One Piece TCG — Importación OP13-OP16 (con fallback)
[2024-01-20 10:30:45] [INFO] Detectando sets disponibles en la API...
[2024-01-20 10:30:50] [INFO] ✓ Sets detectados: ['OP01', 'OP02', ..., 'OP15']
[2024-01-20 10:30:50] [INFO] ⚠ OP16 no disponible. Importando OP13, OP14, OP15...
[2024-01-20 10:30:50] [INFO] Descargando índice completo de cartas...
[2024-01-20 10:30:55] [INFO] ✓ 2500 entradas en el índice

[OP13] Importando 200 cartas...
  [100%] 200/200
  ✓ 150 cartas + 50 variantes

[OP14] Importando 210 cartas...
  [100%] 210/210
  ✓ 160 cartas + 50 variantes

[OP15] Importando 220 cartas...
  [100%] 220/220
  ✓ 165 cartas + 55 variantes

✓ COMPLETADO
Total: 475 cartas + 155 variantes
Tiempo: 87.3s (1.5 minutos)
```

---

### Opción B: Importar sets específicos (versión optimizada)

```bash
# Importar solo OP13 y OP14
python scripts/import_cards_optimized.py --sets OP13 OP14

# Importar un rango OP13-OP15
python scripts/import_cards_optimized.py --sets OP13-OP15

# Importar todos los sets conocidos (por defecto)
python scripts/import_cards_optimized.py
```

---

### Opción C: Importar nuevos sets cuando salgan

```bash
# Cuando salga OP17
python scripts/import_op13_to_op16.py --sets OP13-OP17
# O usar la versión optimizada:
python scripts/import_cards_optimized.py --sets OP13-OP17
```

---

## 🔧 Configuración (Variables de entorno)

Si tu BD usa credenciales diferentes, configura:

```bash
# Windows PowerShell
$env:DB_HOST = "tu-host"
$env:DB_PORT = "5432"
$env:DB_NAME = "tu-base-datos"
$env:DB_USER = "tu-usuario"
$env:DB_PASS = "tu-contraseña"

# Luego ejecutar
python scripts/import_op13_to_op16.py
```

O editar el archivo directamente (líneas 23-29):

```python
DB_CONFIG = {
    "host":     "tu-host",
    "port":     5432,
    "dbname":   "tu-base-datos",
    "user":     "tu-usuario",
    "password": "tu-contraseña",
}
```

---

## 📊 Detalles técnicos

### Diferencias entre scripts

| Aspecto | `import_cards_optimized.py` | `import_op13_to_op16.py` |
|---------|-----|---|
| **Flexibilidad** | Importa cualquier set | Fijo a OP13-OP16 |
| **Detección** | ✅ Automática | ✅ Automática |
| **Fallback** | Manual | ✅ OP15 si falta OP16 |
| **Complejidad** | Mayor | Menor (más simple) |
| **Para usuario** | Para scripts automatizados | Para importación manual |

### Rate limiting

Ambos scripts respetan el rate limiting de la API:

1. Pausa de **0.3s** entre requests (configurable)
2. Si recibe 429 (Too Many Requests):
   - Espera y reintenta
   - Backoff exponencial: 0.5s → 0.75s → 1.125s → máx 30s
   - Hasta 5 reintentos

### Performance

- **Batch commits:** Cada 50 inserciones
- **Índices automáticos:** Para búsqueda rápida
- **Transacciones:** Una por set para atomicidad

---

## 📝 Logs

### Archivo de log

Los logs se escriben automáticamente en:

```
D:\One Piece Scanner\one_piece_card_server\import_op13_to_op16.log
D:\One Piece Scanner\one_piece_card_server\import_cards.log
```

**Ejemplo:**
```
[2024-01-20 10:30:45] [INFO] Sets disponibles: ['OP01', 'OP02', ..., 'OP15']
[2024-01-20 10:30:50] [WARN] OP16 no disponible. Importando hasta OP15...
[2024-01-20 10:31:00] [INFO] ✓ OP13: 150 cartas + 50 variantes
[2024-01-20 10:32:15] [INFO] ✓ COMPLETADO - Total: 475 cartas + 155 variantes
```

---

## ⚠️ Troubleshooting

### Problema: "Error de conexión a BD"

**Causa:** Credenciales incorrectas o BD no accessible

**Solución:**
```bash
# Verifica credenciales en DB_CONFIG
# Prueba conexión manual:
psql -h nozomi.proxy.rlwy.net -p 33325 -U postgres -d railway
```

---

### Problema: "Rate limit - esperando Xs"

**Causa:** API está limitando las requests

**Solución:**
- Es normal — el script auto-reintenta
- Espera a que complete (puede tomar más tiempo)
- No necesitas hacer nada

---

### Problema: "Sets no disponibles (se ignorarán): OP16"

**Causa:** OP16 aún no está en la API

**Solución:**
- El script automáticamente usará OP15 como máximo
- Es el comportamiento esperado del fallback

---

### Problema: "No se encontraron sets en la API"

**Causa:** API inaccesible o problema de conexión

**Solución:**
```bash
# Prueba acceso a la API manualmente:
curl https://optcgapi.com/api/allSetCards/ | head -20
```

---

## 📈 Estadísticas esperadas

### Sets OP13-OP15 (aproximado)

| Set | Cartas | Variantes | Total |
|-----|--------|-----------|-------|
| OP13 | 150-160 | 40-50 | 190-210 |
| OP14 | 160-170 | 40-50 | 200-220 |
| OP15 | 160-170 | 40-50 | 200-220 |
| **Total** | **470-500** | **120-150** | **590-650** |

**Tiempo esperado:** 2-3 minutos (dependiendo de conexión)

---

## 🎯 Para Imu

Después de importar, puedes verificar si Imu se importó:

```bash
# En psql o desde la BD:
SELECT id, name, card_type FROM cards WHERE name ILIKE '%Imu%';
```

Si aparece, ¡está en la BD! El scanner debería encontrarlo.

---

## 📞 Soporte

Si tienes problemas:

1. Revisa el archivo de log: `import_op13_to_op16.log`
2. Verifica que tienes conexión a internet
3. Verifica credenciales de BD
4. Intenta nuevamente — a veces es un timeout temporal

---

## ✅ Checklist post-importación

- [ ] Script completó exitosamente
- [ ] Log muestra "✓ COMPLETADO"
- [ ] Total de cartas es mayor que 0
- [ ] Verificaste en BD que Imu existe: `SELECT * FROM cards WHERE name ILIKE '%Imu%';`
- [ ] Probaste en el scanner que Imu aparece

