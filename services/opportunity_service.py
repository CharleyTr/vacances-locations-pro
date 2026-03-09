"""Identification des opportunités de réservation."""


def booking_opportunities(gaps: list[dict], min_nuits: int = 2) -> list[dict]:
    opportunities = []

    for gap in gaps:
        nuits = gap["nuits"]
        if nuits >= min_nuits:
            if nuits <= 3:
                type_sejour = "🌟 Court séjour (2-3 nuits)"
            elif nuits <= 7:
                type_sejour = "📅 Semaine possible"
            else:
                type_sejour = "🏖️ Long séjour"

            opportunities.append({
                **gap,
                "type": type_sejour,
            })

    return opportunities
