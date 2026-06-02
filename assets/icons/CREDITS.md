# Іконки погоди

Набір **Meteocons** © [Bas Milius](https://github.com/basmilius/weather-icons) —
ліцензія **MIT**.

Файли `*.png` згенеровані зі стилю `fill` пакета `@meteocons/svg-static`
скриптом [`tools/fetch_icons.py`](../../tools/fetch_icons.py).

У рантаймі бот вантажить лише ці PNG через Pillow — `resvg-py`/`cairosvg`
у продакшені **не потрібні**. Якщо файлу іконки немає, `render/icons.py`
малює запасний варіант примітивами Pillow.
