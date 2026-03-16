-- ============================================================
-- CODES PIN PAR PROPRIÉTÉ
-- ============================================================
-- Remplacez les valeurs entre quotes par vos vrais codes PIN
-- avant d'exécuter ce script.
--
-- Le code PIN est haché en SHA-256 pour la sécurité.
-- Pour générer le hash d'un code PIN depuis Python :
--   import hashlib
--   hashlib.sha256("1234".encode()).hexdigest()
--
-- OU utilisez directement l'interface 🏠 Propriétés → Mots de passe
-- (plus simple, le hash est calculé automatiquement)
-- ============================================================

-- ── Option 1 : Saisir le code en clair (Supabase le stockera en clair) ───────
-- Cette option fonctionne car app.py accepte le code en clair OU hashé
-- REMPLACEZ les codes ci-dessous par les vôtres AVANT d'exécuter

UPDATE proprietes SET mot_de_passe = '1234' WHERE id = 1;  -- Le Turenne → code PIN = 1234
UPDATE proprietes SET mot_de_passe = '5678' WHERE id = 2;  -- Villa Tobias (ADMIN) → code PIN = 5678
-- UPDATE proprietes SET mot_de_passe = '9012' WHERE id = 99; -- Appartement Demo → code PIN = 9012

-- ── Option 2 : Stocker les codes hashés (recommandé pour la production) ─────
-- Décommentez et utilisez les hashs générés par la formule Python ci-dessus

-- Exemple pour code "1234" :
-- UPDATE proprietes SET mot_de_passe = '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4' WHERE id = 1;

-- Exemple pour code "5678" :
-- UPDATE proprietes SET mot_de_passe = '1bc1a361f17092bc7af4b2f82bf9194ea9ee2ca49eb2e53e29ef1fc1be1b5aab' WHERE id = 2;

-- ── Vérification ─────────────────────────────────────────────────────────────
SELECT id, nom,
       CASE WHEN mot_de_passe IS NOT NULL THEN '✅ Code PIN configuré'
            ELSE '❌ Pas de code PIN'
       END AS statut_pin
FROM proprietes
WHERE actif = TRUE
ORDER BY id;
