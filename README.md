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

## Comandos principales

- `/drops crear`
- `/drops participantes`
- `/drops quitar`
- `/drops bloquear`
- `/drops finalizar`
- `/drops reroll`
- `/drops cancelar`

