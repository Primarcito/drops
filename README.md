# Drop

Bot de Discord para sorteos dinamicos.

## Idea del sistema

- El mensaje publico del Drop muestra solo el resumen: premio, tiempo, ganadores y cantidad de participantes.
- Los participantes se guardan en SQLite, no en el embed.
- Staff puede ver participantes en paginas, quitar personas y bloquearlas del Drop.
- El bot puede cerrar Drops automaticamente cuando termina el tiempo.

## Primer arranque

1. Crea un entorno virtual.
2. Instala dependencias:

```bash
pip install -r requirements.txt
```

3. Copia `.env.example` a `.env` y completa los IDs.
4. Ejecuta:

```bash
python main.py
```

## Railway

Variables recomendadas:

- `TOKEN` o `DISCORD_TOKEN`: token del bot de Discord.
- `GUILD_IDS`: IDs de los servidores donde se sincronizan rapido los comandos, separados por coma. Ejemplo: `111111111111111111,222222222222222222`.
- `GUILD_ID`: opcional y compatible con la version anterior si solo usas un servidor. Si defines `GUILD_IDS`, esa lista tiene prioridad.
- `DATA_DIR`: opcional. Si usas un volumen persistente en Railway, apuntalo al path del volumen. Ejemplo: `/data`.
- `DROP_CHECK_INTERVAL_SECONDS`: opcional. Cada cuantos segundos revisa cierres automaticos. Por defecto es `1`.
- `EMOJI_DROPS_*_ID`: opcional. IDs de los emojis del Developer Portal. Si no existen, el bot usa emojis unicode.
- `DROP_ADMIN_ROLE_IDS`: opcional. IDs de roles que pueden administrar Drops, separados por coma. Por defecto, `/sorteo panel` y los controles para quitar/bloquear participantes solo aparecen para `1473624624964173952`, `1336825861466488975` y `983987481961717782`. Si usas varios servidores, agrega tambien los IDs de roles equivalentes de cada servidor.
- `DROP_ADMIN_ROLE_NAMES`: opcional. Nombres de roles que pueden administrar Drops, separados por coma.

## Persistencia

- El contador del Drop sale de la tabla `drops` en SQLite.
- La informacion del sorteo, participantes, bloqueados, ganadores y logs queda guardada en `drops.db`.
- En Railway, crea un volumen persistente y usa `DATA_DIR=/data` si montas el volumen en `/data`.
- Al arrancar, el bot imprime el path real de la base de datos con `[DROPS] Base de datos lista: ...`.

## Comandos principales

- `/sorteo crear`: publica un sorteo en el canal. Campos obligatorios: `premio`, `duracion`, `ganadores`. Campo opcional: `requisitos`.
- `/sorteo panel`: abre el panel privado para ver participantes, quitar, bloquear, finalizar, cancelar, hacer reroll y cambiar la foto del premio.
- `/sorteo logs`: abre el historial privado de sorteos finalizados. Limpiar logs solo oculta el historial visible; el numero de Drop sigue aumentando.
