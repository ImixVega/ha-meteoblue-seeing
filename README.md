# Meteoblue Astronomy Seeing for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-custom-41BDF5.svg)](https://hacs.xyz/)

Nieoficjalna integracja Home Assistant do wyświetlania godzinowej prognozy **Astronomy Seeing** dla współrzędnych wybranych w konfiguratorze. Pobiera i interpretuje dane HTML ze strony meteoblue. **Nie korzysta z oficjalnego płatnego API, wbudowanego Scrape ani REST sensorów.**

> [!IMPORTANT]
> Meteoblue nie jest autorem ani sponsorem tej integracji. Publiczna dostępność strony nie oznacza automatycznie uprawnienia do systematycznego pobierania lub redystrybucji danych. Przed używaniem sprawdź bieżące warunki meteoblue. Integracja nie omija ograniczeń i nie używa danych logowania.

## Funkcje

- Konfiguracja nazwy lokalizacji, szerokości i długości geograficznej oraz strefy czasowej z interfejsu HA.
- Pobranie prognozy co **3 godziny** (jeden odczyt dla wszystkich sensorów danej lokalizacji).
- Przesunięcie bieżącego zestawu wartości co godzinę bez dodatkowych żądań.
- Seeing Index 1/2, seeing (arcsec), chmury niskie/średnie/wysokie, jet stream, warstwy turbulencji, gradient, temperatura, wilgotność, iluminacja Księżyca i znacznik ostatniego pobrania.
- Trzy sensory prognozy (`Dzisiaj`, `Jutro`, `Pojutrze`) z tablicą `forecast` w atrybutach; długość zależy od rzeczywiście opublikowanych danych.
- Logowanie błędów i oznaczanie niedostępności w razie braku danych.
- Ikona integracji dostępna lokalnie w Home Assistant 2026.3+.

## Instalacja przez HACS

1. HACS → trzy kropki → **Niestandardowe repozytoria**.
2. Dodaj adres `https://github.com/ImixVega/ha-meteoblue-seeing` jako typ **Integracja**.
3. Zainstaluj i wykonaj restart HA, jeśli wymagany przy pierwszej instalacji/aktualizacji kodu.
4. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Meteoblue Astronomy Seeing**.
5. Ustaw współrzędne i strefę czasową, np. `Europe/Warsaw`.

Możliwa jest też instalacja ręczna: skopiuj `custom_components/meteoblue_seeing/` do `/config/custom_components/`.

## Wykresy

Kompatybilna karta: [Meteoblue Seeing Card](https://github.com/ImixVega/ha-meteoblue-seeing-card) (instalowana osobno jako dodatek typu Dashboard).

## Diagnostyka i ograniczenia

- HTML witryny może się zmienić. W takim wypadku trzeba zaktualizować parser.
- Błędy serwera 403/429 lub błędy parsowania nie są obchodzone automatycznie.
- To społecznościowa wersja `0.1.0`; działała w instalacji użytkownika, ale nie została przetestowana na wszystkich wersjach HA ani lokalizacjach.
- Nie dołączamy zrzutów strony, rzeczywistej lokalizacji użytkownika ani prywatnej konfiguracji.

**Data source:** [meteoblue Astronomy Seeing](https://www.meteoblue.com/en/weather/outdoorsports/seeing/52.230N21.010E).

## License

MIT — see [LICENSE](LICENSE). Third-party forecast data, website content and trademarks are not covered by this license.
