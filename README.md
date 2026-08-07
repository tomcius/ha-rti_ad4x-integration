# RTI AD-4x — integracja Home Assistant

Integracja Home Assistant (domain `rti_ad4x`) dla wzmacniacza dystrybucji
audio **RTI AD-4x** (TCP, port 23) — konfigurowana w pełni przez UI, bez
zależności od MQTT ani żadnego brokera pośredniczącego (w odróżnieniu od
istniejącego, społecznościowego mostka MQTT dla siostrzanego modelu AD-8x).

Protokół sterujący nie jest oficjalnie udokumentowany przez RTI (dostępny
tylko dla integratorów na NDA) — komendy i format odpowiedzi zostały
odtworzone przez bezpośrednie sondowanie żywego urządzenia (fw 1.03.18)
oraz analizę otwartoźródłowego mostka MQTT dla AD-8x.

## Funkcje

Dla każdej z 4 stref:

| Encja | Domain | Zakres |
|---|---|---|
| Zasilanie | `switch` | on/off |
| Wyciszenie | `switch` | on/off |
| Głośność | `number` | 0–75 (0 = cisza, 75 = najgłośniej — odwrócone względem natywnej skali wzmacniacza dla intuicyjnej obsługi) |
| Tony niskie | `number` | -12..12 |
| Tony wysokie | `number` | -12..12 |
| Źródło | `select` | 8 wejść (Lokalne 1–4, Zdalne 1–4) |

Brak powiadomień push ze strony wzmacniacza — integracja odpytuje stan co
15 s (`iot_class: local_polling`).

## Instalacja

### HACS

HACS → ⋮ → Custom repositories → dodaj ten adres repo (kategoria: Integration)
→ zainstaluj → restart Home Assistant → Settings → Devices & Services →
Add Integration → **RTI AD-4x**.

### Ręcznie

Skopiuj `custom_components/rti_ad4x/` do `<config>/custom_components/rti_ad4x/`,
zrestartuj HA, dodaj integrację jak wyżej.

## Konfiguracja

Kreator prosi o adres IP i port (domyślnie 23), sprawdza połączenie z
portem sterującym i próbuje odczytać model/wersję firmware/MAC z
niezabezpieczonej strony statusu wzmacniacza (port 80). Następnie pozwala
nazwać każdą z 4 stref — można to później zmienić przez **Configure** na
wpisie integracji (options flow).

## Protokół (skrót)

- TCP port 23, ASCII, linie zakończone samym `\r` (nie prawdziwy Telnet —
  brak negocjacji opcji).
- Zaraz po połączeniu wysyłana jest sekwencja inicjująca `\x1b2\r`.
- Komendy: `*ZN{zz}{CMD}{wartość}`, np. `*ZN01PWR01` (zasilanie strefy 1
  wł.), `*ZN01VOL45` (głośność), `*ZN01SRC03` (źródło).
- Zapytanie o stan: `*ZN01STA00` → `#01,1,0,3,45` (strefa, zasilanie,
  wyciszenie, źródło, głośność); `*ZN01SET00` → `$01,00,04` (tony
  niskie/wysokie).
- Nierozpoznana komenda → wzmacniacz odpowiada `#?`.
