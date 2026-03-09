def payment_status(row):

    acompte = row.get("acompte", 0)
    prix_total = row.get("prix_total", 0)

    if acompte == 0:
        return "acompte manquant"

    if acompte < prix_total:
        return "solde restant"

    return "payé"
