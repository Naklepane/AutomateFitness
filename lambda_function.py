import json
import requests
import time
from datetime import datetime, timedelta

# Ładowanie konfiguracji z pliku JSON i walidacja konfiguracji
with open("config.json") as config_file:
    config = json.load(config_file)

# Sprawdzenie, czy wszystkie wymagane pola są obecne w konfiguracji (oprócz 'DEBUG_MODE')
required_fields = ["BASE_URL", "LOGIN", "PASSWORD", "CLUB_NAME", "CLASS_NAME", "CLASS_HOUR", "DAYS_BEFORE_BOOKING"]
for field in required_fields:
    if field not in config or not config[field]:
        raise ValueError(f"Missing or empty configuration field: {field}")

# Oddzielne sprawdzenie dla 'DEBUG_MODE' (może być ustawione na True lub False)
if "DEBUG_MODE" not in config:
    raise ValueError("Missing configuration field: DEBUG_MODE")

# Stałe wartości konfiguracyjne
BASE_URL = f'{config["BASE_URL"]}/ClientPortal2'
LOGIN = config["LOGIN"]
PASSWORD = config["PASSWORD"]
CLUB_NAME = config["CLUB_NAME"]
CLASS_NAME = config["CLASS_NAME"]
CLASS_HOUR = config["CLASS_HOUR"]
DAYS_BEFORE_BOOKING = config["DAYS_BEFORE_BOOKING"]
DEBUG_MODE = config["DEBUG_MODE"]

# Końcówki API
LOGIN_ENDPOINT = "/Auth/Login"
CLUBS_ENDPOINT = "/Clubs/GetAvailableClassesClubs"
FILTERS_ENDPOINT = "/Classes/ClassCalendar/GetCalendarFilters"
DAILY_CLASSES_ENDPOINT = "/Classes/ClassCalendar/DailyClasses"
BOOK_CLASS_ENDPOINT = "/Classes/ClassCalendar/BookClass"


# Funkcja pomocnicza do wysyłania żądań POST
def send_post_request(url, payload, session):
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()  # Sprawdzenie statusu HTTP odpowiedzi
        if DEBUG_MODE:
            print(f"Response from {url}: {response.json()}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        if DEBUG_MODE:
            print(f"HTTP Error response from {url}: {response.text}")
        raise RuntimeError(f"HTTP Error: {e.response.status_code}, {response.text}")
    except requests.exceptions.RequestException:
        if DEBUG_MODE:
            print(f"Request Exception response from {url}: {response.text}")
        raise RuntimeError(f"Request Error: {response.text}")


# Zarządzanie sesją w celu automatycznego zamykania połączenia
class SessionManager:
    def __enter__(self):
        self.session = requests.Session()
        self.authenticate_user()  # Autoryzacja użytkownika
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()  # Zamykanie sesji po zakończeniu

    def authenticate_user(self):
        # Logowanie użytkownika do systemu
        login_url = f"{BASE_URL}{LOGIN_ENDPOINT}"
        payload = {
            "RememberMe": False,
            "Login": LOGIN,
            "Password": PASSWORD
        }
        response = send_post_request(login_url, payload, self.session)


# Funkcja zwracająca datę za 'DAYS_BEFORE_BOOKING' dni od teraz
def get_date_after_week():
    future_date = datetime.now() + timedelta(days=DAYS_BEFORE_BOOKING)
    return future_date.strftime("%Y-%m-%d")


# Funkcja czekająca do najbliższej pełnej minuty przed rezerwacją
def wait_until_next_full_minute():
    now = datetime.now()
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    time_to_wait = (next_minute - now).total_seconds()
    time.sleep(time_to_wait)  # Czekanie przez określoną liczbę sekund do pełnej minuty
    print(f"Reached the exact UTC time: {next_minute}. Time for booking request...")


# Pobranie dostępnych klubów
def get_clubs(base_url, session):
    url = f"{base_url}{CLUBS_ENDPOINT}"
    return send_post_request(url, {}, session)


# Pobranie ID klubu na podstawie nazwy
def get_club_id_by_name(clubs, name):
    club_id = next((club["Id"] for club in clubs if club["Name"] == name), None)
    if club_id is None:
        raise ValueError(f"Club '{name}' not found.")
    return club_id


# Pobranie filtrów dla wybranego klubu
def get_filters(base_url, club_id, session):
    url = f"{base_url}{FILTERS_ENDPOINT}"
    payload = {"clubId": club_id}
    return send_post_request(url, payload, session)


# Pobranie ogolnego, tabelarycznego ID zajęć na podstawie ich nazwy
def get_time_table_id_by_class_name(calendar_filters, class_name):
    time_table_id = next(
        (filter['Id'] for filter in calendar_filters['TimeTableFilters'] if filter['Name'] == class_name), None)
    if time_table_id is None:
        raise ValueError(f"Class '{class_name}' not found in the timetable.")
    return time_table_id


# Pobranie listy specyficznych zajęć na dany dzień na podstawie ogolnego ID
def get_filtered_daily_classes(date, club_id, time_table_id, session):
    url = f"{BASE_URL}{DAILY_CLASSES_ENDPOINT}"
    payload = {
        "clubId": club_id,
        "date": date,
        "timeTableId": time_table_id,
    }
    return send_post_request(url, payload, session)


# Pobranie ID konkretnych zajęć na podstawie godziny
def get_class_id_by_time(data, time_str):
    time_to_find = datetime.strptime(time_str, "%H:%M").time()
    class_id = next(
        (class_entry['Id'] for entry in data['CalendarData'] for class_entry in entry['Classes']
         if datetime.strptime(class_entry['StartTime'], "%Y-%m-%dT%H:%M:%S").time() == time_to_find),
        None
    )
    if class_id is None:
        raise ValueError(f"Class at {time_str} not found.")
    return class_id


# Rezerwowanie zajęć na podstawie ID konkretnych zajęć
def book_class(class_id, club_id, session):
    url = f"{BASE_URL}{BOOK_CLASS_ENDPOINT}"
    payload = {
        "classId": class_id,
        "clubId": club_id
    }
    return send_post_request(url, payload, session)


# Główna funkcja wywoływana w AWS Lambda
def lambda_handler(event, context):
    try:
        # Obliczanie daty za 'DAYS_BEFORE_BOOKING' dni
        target_date = get_date_after_week()
        print(
            f'Booking classes "{CLASS_NAME}" at "{target_date} {CLASS_HOUR}" in "{CLUB_NAME}", {DAYS_BEFORE_BOOKING} days before the due date.')

        # Zarządzanie sesją i wysyłanie żądań
        with SessionManager() as user_session:

            # Wyłuskanie ID klubu na podstawie nazwy od użytkownika
            clubs = get_clubs(BASE_URL, user_session)
            club_id = get_club_id_by_name(clubs, CLUB_NAME)
            print(f"[SUCCESS] Club ID successfully established: {club_id}")

            # Wyłuskanie ogólnego ID zajęć na podstawie nazwy od użytkownika
            filters = get_filters(BASE_URL, club_id, user_session)
            time_table_id = get_time_table_id_by_class_name(filters, CLASS_NAME)
            print(f"[SUCCESS] Time Table ID successfully established: {time_table_id}")

            # Wyłuskanie ID dla konkretnych zajęć na podstawie godziny od użytkownika
            filtered_daily_classes = get_filtered_daily_classes(target_date, club_id, time_table_id, user_session)
            class_id = get_class_id_by_time(filtered_daily_classes, CLASS_HOUR)
            print(f"[SUCCESS] Class ID successfully established: {class_id}")

            # Czekanie do pełnej minuty 
            wait_until_next_full_minute()

            # Rezerwowanie zajęć przy wykorzystaniu wszystkich uzyskanych danych
            booking_response = book_class(class_id, club_id, user_session)
            print(f"Booking Response: {booking_response}")

            # Zwracanie odpowiedzi w przypadku sukcesu
            if booking_response:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': '[SUCCESS] Class booked successfully!',
                        'booking_response': booking_response
                    })
                }
            else:
                raise RuntimeError("Failed to book the class.")

    except Exception as e:
        # Łapanie i wypisywanie błędów, zwracanie odpowiedzi z kodem 500
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'Error': str(e)})
        }
