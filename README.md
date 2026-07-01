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
- `APPLICATION_ID`: ID de la aplicacion de Discord.
- `GUILD_ID`: ID del servidor donde se sincronizan rapido los comandos. Recomendado para que `/sorteo` aparezca al reiniciar y no tengas que esperar la cache global de Discord.
- `DATA_DIR`: opcional. Si usas un volumen persistente en Railway, apuntalo al path del volumen. Si no, SQLite puede reiniciarse en redeploys.
- `EMOJI_DROPS_*_ID`: opcional. IDs de los emojis del Developer Portal. Si no existen, el bot usa emojis unicode.
- `DROP_ADMIN_ROLE_IDS`: opcional. IDs de roles que pueden administrar Drops, separados por coma.
- `DROP_ADMIN_ROLE_NAMES`: opcional. Nombres de roles que pueden administrar Drops, separados por coma.

## Comandos principales

- `/sorteo crear`: publica un sorteo en el canal.
- `/sorteo panel`: abre el panel privado para ver participantes, quitar, bloquear, finalizar, cancelar, hacer reroll y cambiar la foto del premio.
