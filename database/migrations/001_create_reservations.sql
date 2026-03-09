-- ============================================================
-- Migration Supabase : Table reservations
-- Vacances-Locations PRO
-- ============================================================

CREATE TABLE IF NOT EXISTS public.reservations (
    id                  SERIAL PRIMARY KEY,
    res_id              UUID DEFAULT gen_random_uuid(),
    ical_uid            TEXT,
    propriete_id        INTEGER NOT NULL DEFAULT 1,

    nom_client          TEXT NOT NULL,
    email               TEXT,
    telephone           TEXT,
    pays                TEXT,

    date_arrivee        DATE NOT NULL,
    date_depart         DATE NOT NULL,
    nuitees             INTEGER GENERATED ALWAYS AS (date_depart - date_arrivee) STORED,

    plateforme          TEXT DEFAULT 'Direct',

    prix_brut           NUMERIC(10, 2) DEFAULT 0,
    commissions         NUMERIC(10, 2) DEFAULT 0,
    frais_cb            NUMERIC(10, 2) DEFAULT 0,
    prix_net            NUMERIC(10, 2) DEFAULT 0,

    menage              NUMERIC(10, 2) DEFAULT 0,
    taxes_sejour        NUMERIC(10, 2) DEFAULT 0,
    base                NUMERIC(10, 2) DEFAULT 0,
    charges             NUMERIC(10, 2) DEFAULT 0,
    pct_commission      NUMERIC(5, 2) DEFAULT 0,

    commissions_hote    NUMERIC(10, 2) DEFAULT 0,
    frais_menage        NUMERIC(10, 2) DEFAULT 0,

    paye                BOOLEAN DEFAULT FALSE,
    sms_envoye          BOOLEAN DEFAULT FALSE,
    post_depart_envoye  BOOLEAN DEFAULT FALSE,

    numero_reservation  TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_reservations_dates
    ON reservations(date_arrivee, date_depart);

CREATE INDEX IF NOT EXISTS idx_reservations_propriete
    ON reservations(propriete_id);

CREATE INDEX IF NOT EXISTS idx_reservations_plateforme
    ON reservations(plateforme);

-- Trigger updated_at automatique
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reservations_updated_at
    BEFORE UPDATE ON reservations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Activer Row Level Security (optionnel mais recommandé)
ALTER TABLE reservations ENABLE ROW LEVEL SECURITY;

-- Politique : accès complet pour les utilisateurs authentifiés
CREATE POLICY "Accès complet authentifiés"
    ON reservations
    FOR ALL
    USING (auth.role() = 'authenticated');

-- Politique : lecture publique (désactiver si données privées)
-- CREATE POLICY "Lecture publique" ON reservations FOR SELECT USING (true);

-- ============================================================
-- Table proprietes (référence)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.proprietes (
    id          SERIAL PRIMARY KEY,
    nom         TEXT NOT NULL,
    adresse     TEXT,
    ical_url    TEXT,
    actif       BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Données initiales
INSERT INTO proprietes (id, nom) VALUES
    (1, 'Villa Tobias'),
    (2, 'Propriété 2')
ON CONFLICT (id) DO NOTHING;

-- Activer RLS
ALTER TABLE proprietes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Lecture propriétés"
    ON proprietes FOR SELECT USING (true);
