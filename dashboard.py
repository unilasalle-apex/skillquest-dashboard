import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page Streamlit
st.set_page_config(layout="wide", page_title="Synthèse SkillQuest", page_icon="📈")

# Noms des fichiers (doivent être dans le même répertoire que ce script)
FILE_NAMES = [
    "xp_SkillQuest_2025-10-06.xlsx",
    "xp_SkillQuest_2025-10-08.xlsx",
    "xp_SkillQuest_2025-10-14.xlsx",
    "xp_SkillQuest_2025-10-24.xlsx",
    "xp_SkillQuest_2025-11-03.xlsx",
    "xp_SkillQuest_2025-11-04.xlsx",
    "xp_SkillQuest_2025-11-05.xlsx",
    "xp_SkillQuest_2025-11-17.xlsx",
    "xp_SkillQuest_2025-11-25.xlsx",
    "xp_SkillQuest_2025-11-28.xlsx",
    "xp_SkillQuest_2025-12-08.xlsx",
    "xp_SkillQuest_2025-12-09.xlsx",
    "xp_SkillQuest_2025-12-10.xlsx",
    "xp_SkillQuest_2025-12-12.xlsx",
    "xp_SkillQuest_2025-12-15.xlsx",
    "xp_SkillQuest_2025-12-16.xlsx",
    "xp_SkillQuest_2025-12-17.xlsx",
    "xp_SkillQuest_2025-12-19.xlsx",
    "xp_SkillQuest_2026-01-05.xlsx",
    "xp_SkillQuest_2026-01-06.xlsx",
    "xp_SkillQuest_2026-01-13.xlsx",
    "xp_SkillQuest_2026-01-19.xlsx",
    "xp_SkillQuest_2026-01-20.xlsx",
    "xp_SkillQuest_2026-01-21.xlsx",
    "xp_SkillQuest_2026-01-23.xlsx",
    "xp_SkillQuest_2026-01-26.xlsx",
    "xp_SkillQuest_2026-02-03.xlsx",
    "xp_SkillQuest_2026-02-09.xlsx",
    "xp_SkillQuest_2026-02-10.xlsx",
    "xp_SkillQuest_2026-02-16.xlsx",
    "xp_SkillQuest_2026-02-17.xlsx",
    "xp_SkillQuest_2026-02-18.xlsx",
    "xp_SkillQuest_2026-03-02.xlsx"
]

# Constantes pour les niveaux et les couleurs
XP_ORDER = {'Non validé': 0, 'Bronze': 1, 'Argent': 2, 'Or': 3}
LEVEL_ORDER = ['Or', 'Argent', 'Bronze', 'Non validé']
COLOR_MAP = {'Or': 'gold', 'Argent': 'skyblue', 'Bronze': 'brown', 'Non validé': 'lightgray'}


# --- Fonctions de préparation des données ---

@st.cache_data
def load_and_prepare_data(file_names):
    """Charge, fusionne, nettoie et calcule les indicateurs nécessaires."""
    
    data_frames = []
    for file_name in file_names:
        try:
            df = pd.read_excel(file_name) 
        except FileNotFoundError:
             st.warning(f"Le fichier {file_name} n'a pas été trouvé. Veuillez vérifier si les fichiers sont dans le répertoire d'exécution.")
             continue
        except Exception as e:
             st.error(f"Erreur lors de la lecture du fichier {file_name} : {e}")
             continue
        data_frames.append(df)

    if not data_frames:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_full = pd.concat(data_frames, ignore_index=True)
    
    # Préparation des colonnes
    df_full['Datetime'] = pd.to_datetime(df_full['Date'] + ' ' + df_full['Heure'])
    df_full['Date_Only'] = df_full['Datetime'].dt.date
    df_full['xp'] = df_full['xp'].fillna('Non validé')
    df_full['xp_level'] = df_full['xp'].map(XP_ORDER)
    df_full['Est_Valide'] = df_full['xp'].isin(['Bronze', 'Argent', 'Or'])
    
    # --- 1. Progression Historique (base pour le temps et les indicateurs) ---
    progression_historique = df_full[['Date_Only', 'Compétence', 'xp_level', 'Est_Valide', 'Mail']].copy()
    progression_historique = progression_historique.sort_values(by='Date_Only')
    
    # Calcul des cumuls et journaliers (pour l'option 'Toutes les Compétences')
    progression_temporelle_globale = progression_historique.groupby('Date_Only').agg(
        Tests_Journaliers=('Est_Valide', 'size'),
        Validations_Journalieres=('Est_Valide', 'sum')
    ).reset_index()

    progression_temporelle_globale['Tests_Cumulés'] = progression_temporelle_globale['Tests_Journaliers'].cumsum()
    progression_temporelle_globale['Validations_Cumulées'] = progression_temporelle_globale['Validations_Journalieres'].cumsum()
    progression_temporelle_globale['Taux_Validation_Journalier'] = (
        progression_temporelle_globale['Validations_Journalieres'] / progression_temporelle_globale['Tests_Journaliers']
    ) * 100
    progression_temporelle_globale['Taux_Validation_Cumule'] = (
        progression_temporelle_globale['Validations_Cumulées'] / progression_temporelle_globale['Tests_Cumulés']
    ) * 100
    
    # --- 2. Préparation du Meilleur Résultat (pour la vue par compétence statique) ---
    df_full_sorted = df_full.sort_values(by=['Mail', 'Compétence', 'Datetime', 'xp_level'], ascending=[True, True, True, False])
    df_latest_best = df_full_sorted.drop_duplicates(subset=['Mail', 'Compétence'], keep='last')
    
    # --- 3. Résultats par Compétence Agrégés (pour le graphique de répartition GLOBAL) ---
    resultats_par_competence = df_latest_best.groupby(['Compétence', 'xp']).size().reset_index(name='Nombre_Etudiants')
    
    # Créer un template pour garantir que tous les niveaux apparaissent
    all_competences = df_latest_best['Compétence'].unique()
    df_template = pd.MultiIndex.from_product([all_competences, LEVEL_ORDER], names=['Compétence', 'xp']).to_frame(index=False)
    resultats_par_competence_full = df_template.merge(resultats_par_competence, on=['Compétence', 'xp'], how='left').fillna(0)
    
    return df_latest_best, resultats_par_competence_full, progression_historique, progression_temporelle_globale

# Charger les données préparées
df_latest_best, resultats_par_competence, progression_historique, progression_temporelle_globale = load_and_prepare_data(FILE_NAMES)


# --- Début du rendu Streamlit ---

if df_latest_best.empty:
    st.title("Tableau de Bord SkillQuest")
    st.error("Impossible de charger les données. Veuillez vérifier les fichiers et les dépendances.")
else:
    # --- Titre et Filtre (Sidebar) ---
    st.title("📈 Synthèse et Évolution SkillQuest")
    
    # Configuration de la Sidebar et du Filtre par Compétence
    st.sidebar.header("Filtres d'Analyse")

    competences_list = sorted(df_latest_best['Compétence'].unique().tolist())
    competences_list.insert(0, "Toutes les Compétences")

    selected_competence = st.sidebar.selectbox(
        "Filtrer par Compétence :",
        competences_list
    )
    
    st.sidebar.markdown("---")
    
    # --- APPLICATION DU FILTRE SUR LES DONNÉES ---
    
    if selected_competence != "Toutes les Compétences":
        # FILTRE : Compétence unique sélectionnée
        df_historique_filtre = progression_historique[progression_historique['Compétence'] == selected_competence]
        df_latest_best_filtre = df_latest_best[df_latest_best['Compétence'] == selected_competence]
        
        # Préparation des données pour le graphique temporel (filtré)
        df_temporel_agg = df_historique_filtre.groupby('Date_Only').agg(
            Tests_Journaliers=('Est_Valide', 'size'),
            Validations_Journalieres=('Est_Valide', 'sum')
        ).reset_index()
        
        if not df_temporel_agg.empty:
            df_temporel_agg['Tests_Cumulés'] = df_temporel_agg['Tests_Journaliers'].cumsum()
            df_temporel_agg['Validations_Cumulées'] = df_temporel_agg['Validations_Journalieres'].cumsum()
            df_temporel_agg['Taux_Validation_Journalier'] = (df_temporel_agg['Validations_Journalieres'] / df_temporel_agg['Tests_Journaliers']) * 100
            df_temporel_agg['Taux_Validation_Cumule'] = (df_temporel_agg['Validations_Cumulées'] / df_temporel_agg['Tests_Cumulés']) * 100
        
        progression_temporelle_affichee = df_temporel_agg
        temporel_title = f"Activité Journalière : {selected_competence}"
        
    else:
        # FILTRE : Toutes les Compétences sélectionnées (Global)
        df_historique_filtre = progression_historique
        df_latest_best_filtre = df_latest_best
        
        # Données globales pour le graphique temporel
        progression_temporelle_affichee = progression_temporelle_globale
        temporel_title = "Activité Journalière Globale"
        
        # Données pour le graphique de répartition
        resultats_filtres = resultats_par_competence

    # --- DÉFINITION DES COLONNES (Mode Journalier par défaut) ---
    y_tests = 'Tests_Journaliers'
    y_validations = 'Validations_Journalieres'
    y_taux = 'Taux_Validation_Journalier'
    y_label = 'Nombre Journalier (Tests/Validations)'
    taux_label = 'Taux de Validation Journalier'
        
    
    # --- 1. Indicateurs Généraux (MIS À JOUR AVEC LE FILTRE) ---
    
    # Les indicateurs généraux affichent toujours les totaux cumulés pour la compétence sélectionnée
    total_tests = df_historique_filtre.shape[0]
    total_validations = df_historique_filtre['Est_Valide'].sum()
    taux_validation_final = (total_validations / total_tests) * 100 if total_tests > 0 else 0


    st.subheader(f"Indicateurs pour {'l\'ensemble des compétences' if selected_competence == 'Toutes les Compétences' else selected_competence}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Tests Totaux Enregistrés", int(total_tests))
    col2.metric("Validations Totales (Bronze+)", int(total_validations))
    col3.metric("Taux de Validation Global", f"{taux_validation_final:.1f}%")
    
    st.divider()

    # --- 2. Évolution dans le Temps (MAJ : Mode Journalier par défaut) ---
    
    st.header("⏳ Activité Journalière (Non cumulée)")
    st.markdown(f"Suivi du nombre de tests effectués et du taux de validation pour **{selected_competence}**.")

    if not progression_temporelle_affichee.empty:
        fig_time = go.Figure()

        # Axe 1 : Tests (Barres)
        fig_time.add_trace(go.Bar(
            x=progression_temporelle_affichee['Date_Only'],
            y=progression_temporelle_affichee[y_tests],
            name='Tests',
            marker_color='lightblue',
            yaxis='y1'
        ))

        # Axe 1 : Validations (Barres)
        fig_time.add_trace(go.Bar(
            x=progression_temporelle_affichee['Date_Only'],
            y=progression_temporelle_affichee[y_validations],
            name='Validations (Bronze+)',
            marker_color='mediumseagreen',
            yaxis='y1'
        ))

        # Axe 2 : Taux de Validation (Ligne)
        fig_time.add_trace(go.Scatter(
            x=progression_temporelle_affichee['Date_Only'],
            y=progression_temporelle_affichee[y_taux],
            name=taux_label,
            mode='lines+markers',
            line=dict(color='red', width=2),
            yaxis='y2'
        ))

        # Configuration des axes
        fig_time.update_layout(
            title=temporel_title,
            barmode='overlay',
            xaxis=dict(title='Date', tickformat="%d %b"),
            yaxis=dict(title=y_label, side='left', showgrid=False),
            yaxis2=dict(title=f"{taux_label} (%)", side='right', overlaying='y', showgrid=True, range=[0, 100]),
            legend=dict(x=0, y=1.1, orientation='h')
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info(f"Aucune donnée historique trouvée pour {selected_competence} dans la période actuelle.")
        
    st.divider()

    # --- 3. Résultats par Compétence (Graphique et Tableau - Affichés UNIQUEMENT si 'Toutes les Compétences' est sélectionné) ---
    
    if selected_competence == "Toutes les Compétences":
        st.header("🎯 Répartition des Niveaux par Compétence (Tous)")
        st.markdown("Visualisation de la répartition des niveaux de validation (Bronze, Argent, Or, Non validé) pour **toutes les compétences**.")
        
        # Graphique de répartition
        resultats_filtres['xp'] = pd.Categorical(resultats_filtres['xp'], categories=LEVEL_ORDER, ordered=True)
        resultats_par_competence_sorted = resultats_filtres.sort_values(by=['Compétence', 'xp'], ascending=[True, False])
        
        fig_competence = px.bar(
            resultats_par_competence_sorted,
            x='Compétence',
            y='Nombre_Etudiants',
            color='xp',
            title="Distribution des Niveaux de Validation par Compétence",
            labels={'Nombre_Etudiants': "Nombre d'Étudiants", 'xp': 'Niveau de Validation'},
            category_orders={'xp': LEVEL_ORDER},
            color_discrete_map=COLOR_MAP,
            height=600
        )
        
        fig_competence.update_layout(
            xaxis={'categoryorder': 'total descending'},
            legend_title_text='Niveau de Validation'
        )
        
        st.plotly_chart(fig_competence, use_container_width=True)

        # Tableau : Taux de Validation par Compétence
        st.subheader("Tableau : Taux de Validation par Compétence")
        
        df_validations = df_latest_best_filtre.groupby('Compétence').agg(
            Validations=('Est_Valide', 'sum'),
            Total_Etudiants=('Est_Valide', 'size')
        ).reset_index()
        
        df_validations['Taux_Validation'] = (df_validations['Validations'] / df_validations['Total_Etudiants']) * 100
        
        df_display = df_validations[['Compétence', 'Total_Etudiants', 'Validations', 'Taux_Validation']].copy()
        df_display.columns = ['Compétence', 'Nb. Étudiants (Résultat Unique)', 'Nb. Validations (Bronze+)', 'Taux Validation (%)']
        df_display['Taux Validation (%)'] = df_display['Taux Validation (%)'].map('{:.1f}%'.format)
        
        st.dataframe(df_display.sort_values(by='Nb. Validations (Bronze+)', ascending=False), use_container_width=True)
