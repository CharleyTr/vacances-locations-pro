from integrations.ical_sync import load_ical

def sync_channels(apartments):

    all_reservations = []

    for apt in apartments:

        if apt["ical_url"]:

            reservations = load_ical(apt["ical_url"])

            all_reservations.extend(reservations)

    return all_reservations
