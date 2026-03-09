import requests
from icalendar import Calendar

def load_ical(url):

    response = requests.get(url)

    calendar = Calendar.from_ical(response.text)

    reservations = []

    for component in calendar.walk():

        if component.name == "VEVENT":

            reservations.append({
                "start": component.get("dtstart").dt,
                "end": component.get("dtend").dt,
                "summary": str(component.get("summary"))
            })

    return reservations
