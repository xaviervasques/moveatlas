# Multimodal FoG (Mendeley r8gmbtv7w2) : format resolu, preuves et decisions

Date : 2026-08-22. Statut : DEBLOQUE (etait differe depuis phase 1 pour risque de mis-mapping).
Outil : `ingest_multimodal_fog.py` (racine du repo), valide sur echantillons reels.
Enjeu : seul jeu EEG + EMG + IMU apparie du programme (12 patients PD, ~3 h 42) ; actif
d'appariement pour l'etage B de KineFM v2 (spec section 7) et premiere source EEG/EMG de MoveAtlas.

## 1. Ce qui bloquait en v1

phase1_remaining.md : "the per-patient task_N.txt is a COMBINED 61-column stream... the value
magnitudes do NOT cleanly align with those offsets (raw gyro counts, a 14-zero block from
disconnected sensors at unexpected positions)". Verdict v1 : DEFER.

## 2. La cle : le README interne + verification signal par signal

Le `afcde674__README.docx` du dossier raw documente exactement le format filtre (60 colonnes,
500 Hz) ; le fichier disque en a 61 car la premiere est un index pandas. Verification faite le
2026-08-22 sur 3 fichiers de patients differents (50 000 lignes chacun) :

| bloc (colonnes disque) | attendu (README) | mesure | verdict |
|---|---|---|---|
| 0 | index | entiers croissants | OK |
| 1 | horodatage, 500 Hz | HH:MM:SS.mmm, dt median 2,00 ms | OK, 500 Hz exact |
| 2-26 (25) | EEG uV (FP1...CP6) | max abs 46-293 | OK, gamme EEG |
| 27-31 (5) | EMG/ECG/EOG, ordre par patient | max abs 340-6000 ; la colonne 29 est partout la plus faible | OK ; 29 = IO (EOG) comme dans la table du README |
| 32-38 | LShank acc3+gyro3+NC | counts IMU ou zeros | OK |
| 39-45 | RShank idem | idem | OK |
| 46-52 | Waist idem | idem | OK |
| 53-59 | Arm acc3+gyro3+SC | counts + 7e colonne 880-1090 (SC) | OK ; le 7e canal des 3 autres blocs est NC (~77, invalide) |
| 60 | label FoG 0/1 | {0,1} ; fichiers avec 60 000 a 663 952 echantillons a 1 | OK, annotation dense experte |

Le "bloc de 14 zeros" v1 = les blocs RShank + Waist (7+7) des patients qui ne portaient que
2 centrales. Position variable car PAR PATIENT ; l'ingestion DETECTE les blocs actifs par
fichier au lieu de faire confiance a une position fixe.

## 3. Decisions d'ingestion (a ratifier, deja implementees)

- D-ING-1 : localisation par POSITION documentee des blocs (LShank -> shank_L, RShank ->
  shank_R, Waist -> lower_back, Arm -> wrist_L), blocs actifs detectes par fichier.
  Constat a signaler aux auteurs : le README dit "2 capteurs = tibia GAUCHE + poignet", mais un
  patient teste a ses donnees dans le bloc RShank. La position fait foi (verifiable), la note
  du README non.
- D-ING-2 : acceleration auto-calibree en g par la norme de gravite mediane PAR CAPTEUR
  (mesure : ~8 600 counts/g, donc MPU6050 configure a +-4g et non +-2g ; l'hypothese fixe
  16 384 aurait donne des g faux d'un facteur 2). Echelle par fichier tracee dans l'audit.
- D-ING-3 : gyroscope divise par 131 (hypothese +-250 dps par defaut MPU6050), NON verifiable
  par la donnee seule ; sans consequence pour l'encodeur (normalisation robuste par canal a
  l'entree), signale dans l'audit.
- D-ING-4 : identite patient par REGROUPEMENT HORAIRE (les taches d'une meme session se
  suivent a l'horloge murale ; seuil 90 min). Preuve sur echantillons : deux hachages
  differents a 22 s d'ecart = un seul patient. Politique anti-fuite : en cas de doute on
  FUSIONNE (fusionner ne fuit jamais ; scinder un patient fuirait). Rapport de groupes emis ;
  attendu : ~11 patients, 008 en deux experiences (README).
- D-ING-5 : sorties = canonical_imu.pkl (contrat IMU standard, labels FoG denses conserves,
  usage eval/segmentation uniquement) + streams_eeg_emg.pkl (EEG 25 canaux nommes, bloc
  EMG/ECG/EOG avec ordre par patient a resoudre sauf EOG, SC, labels) : l'actif d'appariement
  de l'etage B. L'EEG/EMG n'entre JAMAIS dans le pre-entrainement mouvement (regle R1/R2 de la
  spec v2).
- D-ING-6 : filtrage source connu et assume : ACC passe-bas 16 Hz, EEG 0,5-100 Hz, EMG
  10-500 Hz, notch 50 Hz (README). L'ACC de ce jeu ne peut donc pas servir de reference haute
  frequence ; suffisant pour le FOG (trepidation 3-8 Hz).

## 4. Reste a faire

1. Tour : `python ingest_multimodal_fog.py` sur les 56 fichiers (~10-20 min), relire
   patient_grouping_report.csv (verifier ~11-14 sessions, fusionner a la main si un groupe est
   douteux), puis fusionner le manifest dans _canonical_imu_manifest.csv et relancer
   build_catalogue.py. ENSUITE (ajout 2026-08-22) : `python build_canonical_eeg.py --only
   multimodal_fog` et `python build_canonical_emg.py --only multimodal_fog` (contrats WBS 1.3
   et 1.4, testes sur les echantillons de cette session).
2. Attribuer l'ordre EMG par patient (table du README, colonnes 27-31) une fois la
   correspondance session -> ID patient etablie par les effectifs (11 patients, 008 double).
   Le point d'entree existe : remplir configs/multimodal_fog_channel_order.csv puis relancer
   build_canonical_emg.py (C-EMG-1) ; indice mesure sur echantillon : le canal d'indice 3 du
   bloc a une kurtosis de 102 (pics type QRS), candidat ECG a confirmer par la table.
3. FAIT 2026-08-22 : configs/canonical_imu.yaml, stub multimodal_fog remplace par le mapping
   verifie ci-dessus.
4. Signaler aux auteurs l'incoherence README / position des blocs (D-ING-1).
5. Lire l'electrode de reference EEG dans le README.docx du raw (les canonical_eeg portent
   REF_COMMON_UNKNOWN en attendant) et auditer corpus entier le spectre du bloc EMG (sur
   echantillon, centroide 3,8-6,3 Hz : la bande 10-500 Hz annoncee n'est pas verifiee).
