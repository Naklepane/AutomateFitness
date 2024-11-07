# Automatyczny System Rezerwacji Zajęć

Jest to automatyczny system rezerwacji zajęć fitness, który wykorzysta Twoją konfigurację do rezerwacji wybranych przez Ciebie zajęć w klubach korzystających z platformy PerfectGym. System loguje się, pobiera dostępne zajęcia i dokonuje rezerwacji na określoną godzinę. Skrypt jest przystosowany do wdrożenia w AWS Lambda. Użycie opisano na filmie na YouTube "System gwarantujący rezerwację dowolnych zajęć w Fitness Platinium - Python, Endpointy, AWS Lambda".

## Wymagania

- konto AWS (free trial całkowicie wystarczy)

## Konfiguracja

Utwórz plik `config.json` w głównym katalogu projektu. Plik ten powinien zawierać następujące klucze:

```json
{
  "BASE_URL": "https://example.com",
  "LOGIN": "twoja_nazwa_użytkownika",
  "PASSWORD": "twoje_hasło",
  "CLUB_NAME": "Twój Klub Fitness",
  "CLASS_NAME": "Zajęcia Joga",
  "CLASS_HOUR": "10:00",
  "DAYS_BEFORE_BOOKING": 7,
  "DEBUG_MODE": false
}
```

## Opis pól konfiguracyjnych

- **BASE_URL**: Podstawowy URL portalu klienta platformy fitness.
- **LOGIN**: Twój login (nazwa użytkownika lub e-mail) do platformy.
- **PASSWORD**: Twoje hasło do platformy.
- **CLUB_NAME**: Nazwa klubu, w którym chcesz zarezerwować zajęcia.
- **CLASS_NAME**: Nazwa zajęć, które chcesz zarezerwować (np. Joga).
- **CLASS_HOUR**: Godzina zajęć, które chcesz zarezerwować, w formacie HH:MM.
- **DAYS_BEFORE_BOOKING**: Liczba dni, na ile wcześniej przed zajęciami system ma dokonać rezerwacji.
- **DEBUG_MODE**: Określa czy mają zostać wypisane dodatkowe informację w logach


## Obsługa błędów

- Jeśli brakuje jakiegokolwiek wymaganego pola w konfiguracji, system zgłosi błąd.
- Błędy HTTP i błędy żądań są przechwytywane i logowane, a system zwraca kod statusu 500, jeśli działa w środowisku AWS Lambda.

## Uwagi

Podczas zmiany czasu z letniego na zimowy / zimowy na letni, system może spróbować dokonać rezerwacji z przesuniętą godziną, ale jest to zachowanie jednorazowe.

## Licencja

Projekt jest licencjonowany na podstawie licencji MIT.
