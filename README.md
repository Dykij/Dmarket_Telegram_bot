# DMarket Price Monitoring Bot

Sistema monitoringa cen na DMarket s integraciej Telegram-bota dlya uvedomlenij i vzaimodejstviya s pol'zovatelyami. Postroena na asinhronnom programmirovanii s ispol'zovaniem Python i sovremennyh tehnologij.

## Osnovnye vozmozhnosti

- **Podderzhka proksi**: HTTP, SOCKS4, SOCKS5 dlya povysheniya konfidencial'nosti i obhoda ogranichenij
- **Asinhronnaya arhitektura**: Postroena na asyncio i uvloop dlya vysokoj proizvoditel'nosti
- **Ustojchivost'**: Polnaya obrabotka oshibok i ispol'zovanie patterna Circuit Breaker
- **Bezopasnost'**: Validaciya dannyh, zashchita konfidencial'noj informacii
- **Paketnaya obrabotka**: Effektivnaya rabota s bol'shimi ob'emami dannyh
- **Testirovanie**: Vysokoe pokrytie unit-testami
- **Optimizaciya**: Ustraneny osnovnye uzkie mesta proizvoditel'nosti
- **CI/CD**: Prostoj konvejer nepreryvnoj integracii
- **Trassirovka**: Ispol'zovanie Zipkin dlya nekotoryh funkcij
- **Ogranichenie skorosti**: Adaptivnye strategii s eksponencial'noj zaderzhkoj
- **Media v Telegram**: Uvedomleniya s izobrazheniyami, video i animaciej
- **Interaktivnyj interfejs**: Ispol'zovanie inline-klaviatur v Telegram
- **Monitoring**: Sistema proverki sostoyaniya i sbora metrik

## Tekhnicheskij stek

- **Yazyk programmirovaniya**: Python 3.11+
- **Upravlenie zavisimostyami**: Poetry
- **Asinhronnyj frejmvork**: Asyncio
- **Kontejnerizaciya**: Docker, Docker Compose
- **Hranilishche dannyh**: Redis
- **Ocheredi soobshchenij**: RabbitMQ
- **Telegram-bot**: aiogram 3.x
- **Testirovanie**: pytest s podderzhkoj asyncio
- **Kontrol' kachestva koda**: Black, Ruff, Pylint, Mypy
- **Logirovanie**: Strukturirovannoe logirovanie s JSON
- **HTTP-klient**: aiohttp
- **Trassirovka**: Zipkin
- **Serializaciya dannyh**: dataclasses-json, marshmallow

## Ustanovka i zapusk

### Ispol'zuya Poetry (rekomenduetsya)

1. Klonirujte repozitorij:
   ```bash
   git clone https://github.com/yourusername/dmarket_telegram_bot.git
   cd dmarket_telegram_bot
   ```

2. Ustanovite Poetry (esli ne ustanovlen):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Ustanovite zavisimosti:
   ```bash
   poetry install
   ```

4. Nastrojte peremennye okruzheniya:
   ```bash
   cp dmarket_parser.dev.env .env
   # Otredaktirujte .env fajl, dobaviv svoi nastrojki
   ```

5. Zapustite prilozhenie:
   ```bash
   poetry run start
   ```

6. Zapustite obrabotchik dlya analiza dannyh:
   ```bash
   poetry run worker
   ```

### Ispol'zuya Docker

1. Klonirujte repozitorij:
   ```bash
   git clone https://github.com/yourusername/dmarket_telegram_bot.git
   cd dmarket_telegram_bot
   ```

2. Nastrojte peremennye okruzheniya v docker-compose.yml ili env-fajlah

3. Zapustite s Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Konfiguraciya

### Nastrojka Telegram-bota

1. Poluchite token dlya bota cherez @BotFather v Telegram
2. Nastrojte token i drugie parametry v fajle .env:
   ```
   TELEGRAM_API_TOKEN=vash_token
   TELEGRAM_WHITELIST=ID1,ID2
   ```

### Nastrojka proksi

Dobav'te proksi v fajl `utils_mount/dmarket_proxies.txt` v formate:
```
http://user:pass@host:port
socks5://host:port
```

## Apxutektypa

Cuctema coctout u3 cлeдyющux komnohehtoв:

- **DMarket Parser**: И3влekaet дahhbie u3 API DMarket u otnpaвляet ux в oчepeд' RabbitMQ
- **Worker**: O6pa6atbiвaet дahhbie u3 oчepeдu u coxpahяet pe3yл'tatbi в Redis
- **Redis**: Xpahut дahhbie o цehax c metaдahhbimu
- **Telegram Bot**: Пoлyчaet дahhbie u3 Redis u в3aumoдeйctвyet c noл'3oвateляmu

## Pa3pa6otka

### O6hoвлehue 3aвucumocteй

```bash
python scripts/update_dependencies.py
```

### 3anyck tectoв

```bash
poetry run pytest
```

### Фopmatupoвahue u npoвepka koдa

```bash
poetry run black .
poetry run ruff check --fix .
poetry run mypy .
```

## Mohutopuhr u ha6людehue

- **Пpoвepka coctoяhuя**: Mohutopuhr Redis, RabbitMQ u API DMarket
- **Metpuku**: C6op дahhbix o npou3вoдuteл'hoctu u 6u3hec-noka3ateляx
- **Иhterpaцuя**: Пoддepжka Prometheus u Grafana

## Лuцeh3uя

MIT

---

Pa3pa6otaho c nomoщ'ю Poetry 💙
