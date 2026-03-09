from datetime import datetime, timedelta
from services.messaging_service import send_checkin_message

def automate_messages(df):

    today = datetime.today()

    for _, row in df.iterrows():

        if row["date_arrivee"] - timedelta(days=2) == today:

            send_checkin_message(row)
