from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Reservation:
    id:                 int
    propriete_id:       int
    nom_client:         str
    date_arrivee:       date
    date_depart:        date

    email:              Optional[str] = None
    telephone:          Optional[str] = None
    pays:               Optional[str] = None
    plateforme:         str = "Direct"

    prix_brut:          float = 0.0
    commissions:        float = 0.0
    frais_cb:           float = 0.0
    prix_net:           float = 0.0

    menage:             float = 0.0
    taxes_sejour:       float = 0.0
    base:               float = 0.0
    charges:            float = 0.0
    pct_commission:     float = 0.0
    commissions_hote:   float = 0.0
    frais_menage:       float = 0.0

    paye:               bool = False
    sms_envoye:         bool = False
    post_depart_envoye: bool = False

    numero_reservation: Optional[str] = None
    res_id:             Optional[str] = None
    ical_uid:           Optional[str] = None

    @property
    def nuitees(self) -> int:
        return (self.date_depart - self.date_arrivee).days

    @property
    def revenu_par_nuit(self) -> float:
        return round(self.prix_net / self.nuitees, 2) if self.nuitees > 0 else 0.0
