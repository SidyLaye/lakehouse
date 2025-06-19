import streamlit as st
import requests
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="🔐 Détection de Fraude",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .fraud-alert {
        background-color: #ff4444;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin: 1rem 0;
    }
    .safe-alert {
        background-color: #28a745;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin: 1rem 0;
    }
    .warning-alert {
        background-color: #ffc107;
        color: black;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration API
API_URL = "http://fraud-api:8000"  # Remplacez localhost par le nom du service
# Fonctions utilitaires
@st.cache_data
def check_api_status():
    """Vérifie si l'API est accessible"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def create_features_from_inputs(amount, credit_limit, credit_score, use_chip, 
                               online_transaction, num_credit_cards, yearly_income, total_debt):
    """
    Crée un vecteur de features réaliste basé sur les inputs utilisateur
    """
    # ✅ Commencer par des zéros au lieu de valeurs aléatoires
    features = [0.0] * 202
    
    # Calculer des métriques dérivées
    utilization_rate = amount / credit_limit if credit_limit > 0 else 0
    debt_to_income = total_debt / yearly_income if yearly_income > 0 else 0
    
    # ✅ Mapper les vraies features aux bonnes positions
    features[0] = amount / 1000.0                    # Montant normalisé
    features[1] = utilization_rate                   # Taux d'utilisation
    features[2] = debt_to_income                     # Ratio dette/revenu  
    features[3] = credit_score / 850.0               # Score crédit normalisé
    features[4] = float(use_chip)                    # Usage puce (0/1)
    features[5] = float(online_transaction)          # Transaction en ligne (0/1)
    features[6] = num_credit_cards / 10.0            # Nombre cartes normalisé
    features[7] = yearly_income / 100000.0           # Revenu normalisé
    features[8] = total_debt / 10000.0               # Dette totale normalisée
    
    # ✅ Ajouter des indicateurs de risque
    if amount > 5000:  # Transaction élevée
        features[9] = 1.0
    if utilization_rate > 0.8:  # Utilisation élevée
        features[10] = 1.0
    if not use_chip and online_transaction:  # Combinaison risquée
        features[11] = 1.0
    if debt_to_income > 0.4:  # Endettement élevé
        features[12] = 1.0
    if credit_score < 600:  # Score faible
        features[13] = 1.0
        
    return features

def create_test_cases():
    """Crée des cas de test réalistes"""
    base_features = [0.0] * 202
    
    # Cas normal
    normal_features = base_features.copy()
    normal_features[0] = 0.05      # Petit montant
    normal_features[1] = 0.2       # Faible utilisation
    normal_features[2] = 0.1       # Peu d'endettement
    normal_features[3] = 0.85      # Bon score crédit
    normal_features[4] = 1.0       # Avec puce
    normal_features[5] = 0.0       # Pas en ligne
    normal_features[6] = 0.3       # Peu de cartes
    normal_features[7] = 0.5       # Revenu moyen
    
    # Cas suspect
    suspect_features = base_features.copy()
    suspect_features[0] = 0.8      # Montant moyen-élevé
    suspect_features[1] = 0.6      # Utilisation modérée
    suspect_features[2] = 0.4      # Endettement moyen
    suspect_features[3] = 0.5      # Score moyen
    suspect_features[4] = 0.5      # Parfois avec puce
    suspect_features[5] = 0.5      # Parfois en ligne
    suspect_features[6] = 0.2      # Peu de cartes
    suspect_features[7] = 0.3      # Revenu faible
    suspect_features[10] = 1.0     # Flag utilisation élevée
    
    # Cas frauduleux
    fraud_features = base_features.copy()
    fraud_features[0] = 5.0        # Montant très élevé
    fraud_features[1] = 0.95       # Utilisation max
    fraud_features[2] = 0.8        # Endettement élevé
    fraud_features[3] = 0.2        # Score faible
    fraud_features[4] = 0.0        # Pas de puce
    fraud_features[5] = 1.0        # En ligne
    fraud_features[6] = 0.1        # Peu de cartes
    fraud_features[7] = 0.2        # Revenu faible
    fraud_features[9] = 1.0        # Flag montant élevé
    fraud_features[10] = 1.0       # Flag utilisation élevée
    fraud_features[11] = 1.0       # Flag combinaison risquée
    fraud_features[12] = 1.0       # Flag endettement élevé
    fraud_features[13] = 1.0       # Flag score faible
    
    return normal_features, suspect_features, fraud_features

def test_prediction(features, case_name):
    """Teste une prédiction avec debug"""
    try:
        # Afficher les features pour debug
        with st.expander(f"🔍 Debug - Features pour {case_name}"):
            st.write("Premières 15 features:", features[:15])
            st.write("Features non-nulles:", [(i, f) for i, f in enumerate(features[:20]) if f != 0.0])
        
        # Appel API
        response = requests.post(
            f"{API_URL}/predict",
            json={"features": features},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Affichage des résultats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Probabilité", f"{result['fraud_probability']:.1%}")
            with col2:
                st.metric("🔍 Classification", "FRAUDE" if result['is_fraud'] else "NORMALE")
            with col3:
                st.metric("📊 Confiance", result['confidence'])
            
            # Alerte colorée
            if result['fraud_probability'] > 0.7:
                st.markdown(f'<div class="fraud-alert">🚨 ALERTE FRAUDE - {result["fraud_probability"]:.1%}</div>', unsafe_allow_html=True)
            elif result['fraud_probability'] > 0.3:
                st.markdown(f'<div class="warning-alert">⚠️ TRANSACTION SUSPECTE - {result["fraud_probability"]:.1%}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="safe-alert">✅ TRANSACTION SÛRE - {result["fraud_probability"]:.1%}</div>', unsafe_allow_html=True)
                
        else:
            st.error(f"❌ Erreur API: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")

# En-tête principal
st.markdown('<h1 class="main-header">🛡️ Système de Détection de Fraude IA</h1>', unsafe_allow_html=True)

# Vérification de l'API
api_status = check_api_status()
if api_status:
    st.success("✅ API connectée et fonctionnelle")
else:
    st.error("❌ API non accessible. Vérifiez que le service est démarré.")
    st.stop()

# Sidebar avec informations
with st.sidebar:
    st.header("ℹ️ Informations Système")
    st.info(f"🕒 Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}")
    
    # Bouton de test API
    if st.button("🔄 Tester la connexion API"):
        try:
            response = requests.get(f"{API_URL}/model/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                st.success("✅ API OK")
                st.json(info)
            else:
                st.error(f"❌ Erreur: {response.status_code}")
        except Exception as e:
            st.error(f"❌ {str(e)}")

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["💳 Analyse Transaction", "⚡ Tests Rapides", "📈 Dashboard"])

with tab1:
    st.header("💳 Analyse d'une Transaction")
    
    # Formulaire de saisie
    with st.form("transaction_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Informations Transaction")
            amount = st.number_input("💰 Montant (€)", min_value=0.01, max_value=50000.0, value=100.0, step=0.01)
            credit_limit = st.number_input("💎 Limite de crédit (€)", min_value=100.0, max_value=100000.0, value=5000.0, step=100.0)
            use_chip = st.checkbox("🔒 Utilisation de la puce", value=True)
            online_transaction = st.checkbox("🌐 Transaction en ligne", value=False)
        
        with col2:
            st.subheader("👤 Profil Client")
            credit_score = st.slider("⭐ Score de crédit", min_value=300, max_value=850, value=650, step=10)
            yearly_income = st.number_input("💼 Revenu annuel (€)", min_value=0, max_value=500000, value=35000, step=1000)
            total_debt = st.number_input("💸 Dette totale (€)", min_value=0, max_value=200000, value=5000, step=500)
            num_credit_cards = st.selectbox("💳 Nombre de cartes de crédit", options=list(range(1, 11)), index=1)
        
        # Métriques calculées
        utilization_rate = amount / credit_limit if credit_limit > 0 else 0
        debt_to_income = total_debt / yearly_income if yearly_income > 0 else 0
        
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            color = "red" if utilization_rate > 0.3 else "green"
            st.metric("📊 Taux d'utilisation", f"{utilization_rate:.1%}")
        with col_metric2:
            color = "red" if debt_to_income > 0.4 else "green"
            st.metric("📈 Ratio dette/revenu", f"{debt_to_income:.1%}")
        with col_metric3:
            score_level = "Excellent" if credit_score >= 750 else "Bon" if credit_score >= 650 else "Moyen" if credit_score >= 550 else "Faible"
            st.metric("⭐ Niveau crédit", score_level)
        
        submitted = st.form_submit_button("🔍 Analyser la Transaction", use_container_width=True)
        
        if submitted:
            with st.spinner("🔄 Analyse en cours..."):
                try:
                    # Créer les features de manière intelligente
                    features = create_features_from_inputs(
                        amount, credit_limit, credit_score, use_chip,
                        online_transaction, num_credit_cards, yearly_income, total_debt
                    )
                    
                    # Debug des inputs
                    with st.expander("🔍 Debug - Analyse des inputs"):
                        st.write("**Inputs utilisateur:**")
                        st.write({
                            "Montant": amount,
                            "Limite crédit": credit_limit,
                            "Utilisation": f"{utilization_rate:.1%}",
                            "Dette/Revenu": f"{debt_to_income:.1%}",
                            "Score crédit": credit_score,
                            "Avec puce": use_chip,
                            "En ligne": online_transaction
                        })
                        st.write("**Features générées (15 premières):**", features[:15])
                    
                    # Appel API
                    response = requests.post(
                        f"{API_URL}/predict",
                        json={"features": features},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Affichage résultats
                        st.markdown("---")
                        st.subheader("📊 Résultats de l'Analyse")
                        
                        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                        with col_res1:
                            st.metric("🎯 Probabilité Fraude", f"{result['fraud_probability']:.1%}")
                        with col_res2:
                            st.metric("🔍 Classification", "FRAUDE" if result['is_fraud'] else "NORMALE")
                        with col_res3:
                            st.metric("📊 Confiance", result['confidence'])
                        with col_res4:
                            risk_level = "ÉLEVÉ" if result['fraud_probability'] > 0.7 else "MOYEN" if result['fraud_probability'] > 0.3 else "FAIBLE"
                            st.metric("⚠️ Niveau de Risque", risk_level)
                        
                        # Alerte visuelle
                        if result['fraud_probability'] > 0.7:
                            st.markdown(f'<div class="fraud-alert">🚨 ALERTE FRAUDE DÉTECTÉE - {result["fraud_probability"]:.1%} de probabilité</div>', unsafe_allow_html=True)
                            st.warning("🛡️ **Actions recommandées:** Bloquer la transaction, contacter le client, vérifier l'identité.")
                        elif result['fraud_probability'] > 0.3:
                            st.markdown(f'<div class="warning-alert">⚠️ TRANSACTION SUSPECTE - {result["fraud_probability"]:.1%} de probabilité</div>', unsafe_allow_html=True)
                            st.info("🔍 **Actions recommandées:** Vérification supplémentaire, authentification renforcée.")
                        else:
                            st.markdown(f'<div class="safe-alert">✅ TRANSACTION SÉCURISÉE - {result["fraud_probability"]:.1%} de probabilité</div>', unsafe_allow_html=True)
                            st.success("✅ **Statut:** Transaction approuvée automatiquement.")
                        
                        # Graphique de probabilité
                        import plotly.graph_objects as go
                        
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number",
                            value = result['fraud_probability'] * 100,
                            title = {'text': "Probabilité de Fraude (%)"},
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            gauge = {
                                'axis': {'range': [None, 100]},
                                'bar': {'color': "darkblue"},
                                'steps': [
                                    {'range': [0, 30], 'color': "lightgreen"},
                                    {'range': [30, 70], 'color': "yellow"},
                                    {'range': [70, 100], 'color': "red"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 90
                                }
                            }
                        ))
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.error(f"❌ Erreur API: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

with tab2:
    st.header("⚡ Tests Rapides Prédéfinis")
    st.info("🧪 Testez le modèle avec des cas prédéfinis pour valider son comportement.")
    
    # Créer les cas de test
    normal_features, suspect_features, fraud_features = create_test_cases()
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        st.subheader("✅ Cas Normal")
        st.write("• Petit montant (50€)")
        st.write("• Faible utilisation (20%)")
        st.write("• Bon score crédit")
        st.write("• Avec puce sécurisée")
        if st.button("🧪 Tester Transaction Normale", use_container_width=True):
            test_prediction(normal_features, "Transaction normale")
    
    with col_test2:
        st.subheader("⚠️ Cas Suspect")
        st.write("• Montant moyen (800€)")
        st.write("• Utilisation modérée (60%)")
        st.write("• Score crédit moyen")
        st.write("• Profil mixte")
        if st.button("🧪 Tester Transaction Suspecte", use_container_width=True):
            test_prediction(suspect_features, "Transaction suspecte")
    
    with col_test3:
        st.subheader("🚨 Cas Frauduleux")
        st.write("• Gros montant (5000€)")
        st.write("• Utilisation maximale (95%)")
        st.write("• Score crédit faible")
        st.write("• Sans puce, en ligne")
        if st.button("🧪 Tester Transaction Frauduleuse", use_container_width=True):
            test_prediction(fraud_features, "Transaction frauduleuse")
    
    # Test personnalisé
    st.markdown("---")
    st.subheader("🎛️ Test Personnalisé")
    
    with st.expander("📝 Créer un test personnalisé"):
        col_custom1, col_custom2 = st.columns(2)
        
        with col_custom1:
            custom_amount = st.number_input("Montant custom", value=1000.0)
            custom_utilization = st.slider("Taux d'utilisation", 0.0, 1.0, 0.3)
            custom_score = st.slider("Score crédit (normalisé)", 0.0, 1.0, 0.7)
        
        with col_custom2:
            custom_chip = st.selectbox("Puce", [0.0, 1.0], index=1)
            custom_online = st.selectbox("En ligne", [0.0, 1.0], index=0)
            custom_debt = st.slider("Ratio dette", 0.0, 1.0, 0.2)
        
        if st.button("🧪 Tester Configuration Custom", use_container_width=True):
            custom_features = [0.0] * 202
            custom_features[0] = custom_amount / 1000.0
            custom_features[1] = custom_utilization
            custom_features[2] = custom_debt
            custom_features[3] = custom_score
            custom_features[4] = custom_chip
            custom_features[5] = custom_online
            
            # Ajouter des flags selon les valeurs
            if custom_amount > 5000:
                custom_features[9] = 1.0
            if custom_utilization > 0.8:
                custom_features[10] = 1.0
            if custom_chip == 0.0 and custom_online == 1.0:
                custom_features[11] = 1.0
            
            test_prediction(custom_features, "Configuration personnalisée")

with tab3:
    st.header("📈 Dashboard de Monitoring")
    
    # Métriques simulées
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Transactions Jour", "1,234", "↗️ +5%")
    with col2:
        st.metric("🚨 Fraudes Détectées", "23", "↘️ -12%")
    with col3:
        st.metric("✅ Précision Modèle", "94.2%", "↗️ +1.2%")
    with col4:
        st.metric("⚡ Temps Réponse", "145ms", "↘️ -23ms")
    
    # Graphiques simulés
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📊 Évolution des Fraudes")
        # Données simulées
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        fraud_data = np.random.poisson(5, 30)
        
        import plotly.express as px
        fig = px.line(x=dates, y=fraud_data, title="Fraudes par jour")
        fig.update_layout(xaxis_title="Date", yaxis_title="Nombre de fraudes")
        st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("🎯 Distribution des Scores")
        # Données simulées
        scores = np.random.beta(2, 8, 1000)  # Distribution typique de scores de fraude
        
        fig = px.histogram(x=scores, title="Distribution des probabilités de fraude", 
                          nbins=50, labels={'x': 'Probabilité', 'y': 'Fréquence'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Alertes récentes
    st.subheader("🔔 Alertes Récentes")
    
    alerts_data = {
        "Heure": ["14:23:45", "14:18:12", "14:15:33", "14:10:07"],
        "Type": ["🚨 FRAUDE", "⚠️ SUSPECT", "🚨 FRAUDE", "⚠️ SUSPECT"],
        "Montant": ["2,450€", "890€", "5,200€", "1,100€"],
        "Probabilité": ["94.2%", "67.8%", "98.1%", "45.3%"],
        "Statut": ["Bloquée", "En attente", "Bloquée", "Approuvée"]
    }
    
    df_alerts = pd.DataFrame(alerts_data)
    st.dataframe(df_alerts, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; margin-top: 2rem;'>
    🚀 <b>Système de Détection de Fraude IA</b> | FastAPI + Streamlit + Docker<br>
    🛡️ Modèle: Regression Logistique | 📊 Features: 202 | ⚡ Temps réel
</div>
""", unsafe_allow_html=True)
